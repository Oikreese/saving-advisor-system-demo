"""
Firestore プライマリdataベース 基づくrecommendationAPIエンドPoints
newアーキテクチャ：すべて 読み書きoperations Firestore み 対象 し、BigQuery ETL 介してdata 取得するanalysisdataベース して機能します
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import json
import re

from app.models.assets import AssetType, UserPortfolio, UserAsset
from app.models.recommendations import (
    AssetRecommendation, MultiAgentResponse, 
    RecommendationFeedbackRequest, RecommendationStatus, RejectionReason,
    RegenerationRequest, RecommendationDetail
)
from app.agents.multi_agent_system import MultiAgentSystem
from app.services.firestore.firestore_primary_service import get_firestore_primary_service, FirestorePrimaryService
from app.services.llm.openai_service import OpenAIService, get_openai_service
from app.core.logging import logger

router = APIRouter()

# グローバルインスタンス
multi_agent_system = MultiAgentSystem()

@router.get("/analyze/{user_id}", response_model=MultiAgentResponse)
async def analyze_user_portfolio_v2(
    user_id: str,
    force_fresh: bool = False,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    userportfolioanalysis - Firestore プライマリdataベース 基づく
    特性：
    - singledataソース（Firestore）
    - 簡素化されたdata取得ロジック
    - 高速な応答時間
    """
    try:
        start_time = datetime.now()
        logger.info(f"portfolioanalysis開始: user_id={user_id}, force_fresh={force_fresh}")
        
        # 1. recent AIanalysis結果 取得しよう 試みます（強制リフレッシュしない場合）
        if not force_fresh:
            cached_analysis = await firestore_service.get_recent_ai_analysis(
                user_id, 'portfolio_analysis', max_age_hours=12
            )
            if cached_analysis:
                analysis_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"キャッシュされたanalysis結果 返します ({analysis_time:.2f}ms)")
                
                # 资产类型转换：从英文转换为日文（兼容旧数据）
                asset_type_mapping = {
                    'Points': 'ポイント',
                    'Earnings': '売上金・給与・報酬',
                    'Items': 'モノ',
                    'Giga': 'ギガ',
                    'Stablecoin': 'ステーブルコイン'
                }
                
                def convert_asset_types_in_dict(data):
                    """递归转换字典中的资产类型"""
                    if isinstance(data, dict):
                        if 'asset_type' in data and data['asset_type'] in asset_type_mapping:
                            data['asset_type'] = asset_type_mapping[data['asset_type']]
                        for value in data.values():
                            convert_asset_types_in_dict(value)
                    elif isinstance(data, list):
                        for item in data:
                            convert_asset_types_in_dict(item)
                
                # ai_response 从数据库读取时已经是字典（JSON 类型）
                ai_response = cached_analysis.get('ai_response', {})
                if not isinstance(ai_response, dict):
                    # 如果是字符串，尝试解析
                    if isinstance(ai_response, str):
                        try:
                            ai_response = json.loads(ai_response)
                        except:
                            ai_response = {}
                    else:
                        ai_response = {}
                
                # 转换所有嵌套的资产类型
                convert_asset_types_in_dict(ai_response)
                
                analyses = ai_response.get('analyses', [])
                consensus_recommendations = ai_response.get('consensus_recommendations', [])
                
                # 結果 build
                return MultiAgentResponse(
                    user_id=user_id,
                    analyses=analyses,
                    consensus_recommendations=consensus_recommendations,
                    conflicting_opinions=ai_response.get('conflicting_opinions', []),
                    overall_assessment=ai_response.get('overall_assessment', ''),
                    generated_at=datetime.fromisoformat(cached_analysis.get('created_at'))
                )
        
        # 2. userportfoliodata 取得
        portfolio = await firestore_service.get_user_portfolio(user_id)
        
        # 3. newAIanalysis execute
        analysis_result = await multi_agent_system.analyze_portfolio(portfolio)
        
        # 4. analysis結果 Firestore save
        session_id = await firestore_service.save_ai_analysis(
            user_id=user_id,
            session_type='portfolio_analysis',
            input_data={'portfolio_total_value': portfolio.total_assets},
            ai_response=analysis_result.model_dump(),
            processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
        )
        
        analysis_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"portfolioanalysis完了: user_id={user_id} ({analysis_time:.2f}ms), session_id={session_id}")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"portfolioanalysisエラー: {e}")
        raise HTTPException(status_code=500, detail="portfolioanalysis failed")

@router.post("/feedback", status_code=204)
async def record_recommendation_feedback_v2(
    request: RecommendationFeedbackRequest,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    recommendationfeedback 記録 - Firestoreへ single書き込み
    特性：
    - 簡素化された書き込みロジック
    - 高速応答
    - ETL 介してBigQueryへ自動同期
    """
    try:
        start_time = datetime.now()
        logger.info(f"recommendationfeedback受信: user_id={request.user_id}, recommendation_id={request.recommendation_id}")
        
        # 拒否理由 column挙型 処理
        feedback_data = request.model_dump(mode='json')
        if request.rejection_reason:
            try:
                reason_enum = RejectionReason[request.rejection_reason]
                feedback_data['rejection_reason'] = reason_enum.value
            except KeyError:
                logger.warning(f"無効な拒否理由: {request.rejection_reason}")
                feedback_data['rejection_reason'] = request.rejection_reason
        
        # Firestoreへdirectly書き込み（singledataソース）
        feedback_id = await firestore_service.save_recommendation_feedback(feedback_data)
        
        if feedback_id:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"recommendationfeedback savesuccess: {feedback_id} ({response_time:.2f}ms)")
        else:
            logger.error("recommendationfeedback save failed")
            raise HTTPException(status_code=500, detail="feedback save failed")
        
        return
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"recommendationfeedback save failed: {e}")
        raise HTTPException(status_code=500, detail="feedback save failed")

@router.get("/feedback/history/{user_id}")
async def get_user_feedback_history_v2(
    user_id: str,
    limit: int = 10,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    userfeedback履歴 取得 - Firestore from 読み取り
    特性：
    - 高速クエリ
    - リアルタイムdata
    """
    try:
        start_time = datetime.now()
        
        history = await firestore_service.get_user_feedback_history(user_id, limit)
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"user{user_id} feedback履歴取得: {len(history)}件 ({response_time:.2f}ms)")
        
        return {
            'user_id': user_id,
            'feedback_history': history,
            'total_count': len(history),
            'response_time_ms': response_time,
            'data_source': 'firestore_primary'
        }
        
    except Exception as e:
        logger.error(f"feedback履歴 取得 failed: {e}")
        raise HTTPException(status_code=500, detail="feedback履歴 取得 failed")

@router.post("/regenerate", response_model=Optional[RecommendationDetail])
async def regenerate_recommendation_v2(
    request: RegenerationRequest,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service),
    llm_service: OpenAIService = Depends(get_openai_service),
):
    """
    recommendationregenerate - Firestoredata 基づく
    userfeedback 応じて、single 最適な代替案 generateします。
    """
    logger.critical(">>> EXECUTING FINAL FIX - V4 <<<") # 診断用ログ
    try:
        start_time = datetime.now()
        logger.info(f"recommendationregenerate開始: user_id={request.user_id}, agent={request.agent_name}")
        
        portfolio_task = firestore_service.get_user_portfolio(request.user_id)
        feedback_task = firestore_service.get_user_feedback_history(request.user_id, limit=10)
        
        portfolio, feedback_history = await asyncio.gather(portfolio_task, feedback_task)
        
        formatted_feedback = _format_feedback_for_prompt(feedback_history)
        
        regeneration_prompt = f"""
user 以前 提案 拒否しました。以下 情報 based on、元 提案 代わる**最も 確な代替案 1つだけ**提案してください。

[user情報]
- 現在 総asset: {portfolio.total_assets:,.0f}円
- 提案カテゴリ: {request.agent_name}

[拒否された提案へ feedback]
- 拒否理由: {request.rejection_reason}
- 詳細コメント: {request.rejection_detail or 'なし'}

[過去 feedback傾向]
{formatted_feedback}

[指示]
user feedback 現在 asset状況 note深くanalysisし、具体  、user すぐ 行動 移せるような、single new提案 generateしてください。
回答 必ず "title", "description", "potential_gain"  キー includingJSONオブジェクト形式 出力してください。
**"potential_gain" 値 必ず整数（例: 5000） してください。説明文 含めない ください。**
"""
        
        new_recommendation_response = await llm_service.generate_completion(
            regeneration_prompt,
            max_tokens=600,
            temperature=0.5,
            json_mode=True
        )
        
        if new_recommendation_response:
            new_recommendation = _parse_regeneration_response(new_recommendation_response)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"recommendationregenerate完了: {response_time:.2f}ms")
            
            return new_recommendation
        
        else:
            logger.warning("LLM よるrecommendationgeneratefailed")
            raise HTTPException(status_code=500, detail="recommendationgeneratefailed")
            
    except Exception as e:
        logger.error(f"recommendationregeneratefailed: {e}")
        raise HTTPException(status_code=500, detail="recommendationregeneratefailed")

@router.get("/assets/{user_id}")
async def get_user_assets_v2(
    user_id: str,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    userasset 取得 - Firestore from directly読み取り
    特性：
    - リアルタイムdata
    - 高速応答
    - singledataソース
    """
    try:
        start_time = datetime.now()
        
        assets_data = await firestore_service.get_user_current_assets(user_id)
        
        if not assets_data:
            raise HTTPException(status_code=404, detail=f"user{user_id} アセットdata 見つかりません")
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"user{user_id} asset取得: ({response_time:.2f}ms)")
        
        return {
            'user_id': user_id,
            'assets': assets_data,
            'response_time_ms': response_time,
            'data_source': 'firestore_primary',
            'last_updated': assets_data.get('last_updated')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"userasset 取得 failed: {e}")
        raise HTTPException(status_code=500, detail="userasset 取得 failed")

@router.post("/assets/{user_id}")
async def update_user_assets_v2(
    user_id: str,
    assets_data: Dict[str, Any],
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    userasset update - Firestoreへdirectly書き込み
    特性：
    - リアルタイムupdate
    - single書き込みソース
    - ETL 自動トリガー
    """
    try:
        start_time = datetime.now()
        
        success = await firestore_service.save_user_assets(user_id, assets_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="assetdata save failed")
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"user{user_id} assetupdate: ({response_time:.2f}ms)")
        
        return {
            'user_id': user_id,
            'status': 'success',
            'message': 'assetdata updateされました',
            'response_time_ms': response_time,
            'etl_queued': True  # data ETLキュー appendされました
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"userasset update failed: {e}")
        raise HTTPException(status_code=500, detail="userasset update failed")

@router.get("/market/valuation/{category_id}/{condition}")
async def get_market_valuation_v2(
    category_id: int,
    condition: int,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    市場評価額 取得 - Firestore from 読み取り
    特性：
    - 高速クエリ
    - リアルタイム市場data
    """
    try:
        start_time = datetime.now()
        
        valuation_data = await firestore_service.get_market_valuation(category_id, condition)
        
        if not valuation_data:
            raise HTTPException(
                status_code=404, 
                detail=f"カテゴリ{category_id}、状態{condition} 市場評価data 見つかりません"
            )
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"市場評価額取得 cat_{category_id}_cond_{condition}: ({response_time:.2f}ms)")
        
        return {
            'category_id': category_id,
            'condition': condition,
            'valuation': valuation_data,
            'response_time_ms': response_time,
            'data_source': 'firestore_primary'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"市場評価額 取得 failed: {e}")
        raise HTTPException(status_code=500, detail="市場評価額 取得 failed")

@router.get("/user/activity/{user_id}")
async def get_user_activity_summary_v2(
    user_id: str,
    days: int = 30,
    firestore_service: FirestorePrimaryService = Depends(get_firestore_primary_service)
):
    """
    user活動概要 取得 - Firestoredata 基づく
    特性：
    - リアルタイム活動統計
    - 高速集計クエリ
    """
    try:
        start_time = datetime.now()
        
        activity_summary = await firestore_service.get_user_activity_summary(user_id, days)
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"user{user_id} 活動概要取得: ({response_time:.2f}ms)")
        
        return {
            'user_id': user_id,
            'activity_summary': activity_summary,
            'response_time_ms': response_time,
            'data_source': 'firestore_primary'
        }
        
    except Exception as e:
        logger.error(f"user活動概要 取得 failed: {e}")
        raise HTTPException(status_code=500, detail="user活動概要 取得 failed")

# ==================== ヘルパー関数 ====================
# _get_portfolio_from_firestore 関数  FirestorePrimaryService.get_user_portfolio  移動しました

def _format_feedback_for_prompt(feedback_history: List[Dict[str, Any]]) -> str:
    """feedback履歴 prompt用 フォーマットする"""
    if not feedback_history:
        return "これ until user from  具体 なfeedback not available。"
    
    formatted_items = []
    for feedback in feedback_history[:5]:  # 最new5件 みuse
        status = feedback.get('status', 'unknown')
        reason = feedback.get('rejection_reason', '')
        detail = feedback.get('rejection_feedback', '')
        
        if status == 'rejected' and reason:
            item = f"- 拒否理由：{reason}"
            if detail:
                item += f"、詳細feedback：{detail}"
            formatted_items.append(item)
    
    return "\n".join(formatted_items) if formatted_items else "user recent、拒否feedback していません。"

def _parse_regeneration_response(response_text: str) -> Optional[RecommendationDetail]:
    """LLM from  JSON応答 parseし、potential_gain 堅牢 抽出する"""
    logger.critical(f">>> PARSING WITH FINAL FIX - V4 <<< RESPONSE: {response_text}") # 診断用ログ
    try:
        parsed_data = json.loads(response_text)
        
        # 必須キー exists チェック
        if not all(k in parsed_data for k in ["title", "description", "potential_gain"]):
            logger.warning(f"JSON応答 必要なキー not available: {parsed_data}")
            raise ValueError("Missing required keys in JSON response")

        # potential_gain 堅牢 parse
        gain_value = parsed_data.get("potential_gain")
        potential_gain = 0.0
        if isinstance(gain_value, (int, float)):
            potential_gain = float(gain_value)
        elif isinstance(gain_value, str):
            # stringcolumn from 最初 数値 抽出
            numbers = re.findall(r'\d+', gain_value)
            if numbers:
                potential_gain = float(numbers[0])
        
        return RecommendationDetail(
            title=parsed_data["title"],
            description=parsed_data["description"],
            potential_gain=potential_gain
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"regenerateレスポンス JSONparse failed: {e}. Raw response: {response_text}")
        # parsefailed時 、userフレンドリーなエラーメッセージ 返す
        return RecommendationDetail(
            title="提案 generateエラー",
            description="AI よるnew提案 generate中 エラー 発生しました。しばらくして from もう一度お試しください。",
            potential_gain=0.0
        )

# 並行operations for asyncio インポート
import asyncio
