"""
Saving Advisor gRPC服务实现

使用数据访问抽象层，支持完整的微服务功能
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import logging

from app.grpc_services.generated.saving_advisor_pb2 import *
from app.grpc_services.generated.saving_advisor_pb2_grpc import SavingAdvisorServiceServicer

# 使用数据访问抽象层
from app.services.data.factory import (
    get_user_data_service,
    get_market_data_service,
    get_feedback_service
)

# 业务逻辑服务
from app.services.core.analysis_service import get_core_analysis_service
from app.services.core.recommendation_service import get_core_recommendation_service
from app.agents.multi_agent_system import MultiAgentSystem
from app.services.utils.visualization_service import get_visualization_service
from app.services.utils.task_service import get_task_service

from app.core.logging import logger


class SavingAdvisorServiceImpl(SavingAdvisorServiceServicer):
    """
    Saving Advisor gRPC服务实现
    
    使用数据访问抽象层，为微服务架构做准备
    """
    
    def __init__(self):
        """初始化服务"""
        # 数据访问层
        self.user_data_service = get_user_data_service()
        self.market_data_service = get_market_data_service()
        self.feedback_service = get_feedback_service()
        
        # 业务逻辑层
        self.analysis_service = get_core_analysis_service()
        self.recommendation_service = get_core_recommendation_service()
        self.multi_agent_system = MultiAgentSystem()
        self.visualization_service = get_visualization_service()
        self.task_service = get_task_service()
        
        logger.info("SavingAdvisorServiceImpl initialized with data abstraction layer")
    
    async def HealthCheck(self, request, context):
        """健康检查"""
        try:
            return HealthResponse(
                status="healthy",
                service="saving_advisor_grpc",
                version="2.0.0",
                timestamp=str(int(time.time()))
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthResponse(
                status="unhealthy",
                service="saving_advisor_grpc", 
                version="2.0.0",
                timestamp=str(int(time.time()))
            )
    
    async def GetUserPortfolio(self, request, context):
        """获取用户投资组合"""
        try:
            logger.info(f"Getting portfolio for user: {request.user_id}")
            
            # 使用数据抽象层获取用户组合
            portfolio = await self.user_data_service.get_user_portfolio(request.user_id)
            
            if not portfolio:
                return PortfolioResponse(
                    success=False,
                    error_message=f"Portfolio not found for user {request.user_id}",
                    timestamp=str(int(time.time()))
                )
            
            # 转换为gRPC消息格式
            grpc_assets = []
            for asset in portfolio.assets:
                grpc_asset = UserAsset(
                    asset_type=asset.asset_type,
                    current_value=float(asset.current_value),
                    target_allocation=float(getattr(asset, 'target_allocation', 0)),
                    last_updated=getattr(asset, 'last_updated', '')
                )
                grpc_assets.append(grpc_asset)
            
            grpc_portfolio = UserPortfolio(
                user_id=portfolio.user_id,
                assets=grpc_assets,
                total_value=float(portfolio.total_value),
                last_updated=getattr(portfolio, 'last_updated', '')
            )
            
            return PortfolioResponse(
                portfolio=grpc_portfolio,
                success=True,
                timestamp=str(int(time.time()))
            )
            
        except Exception as e:
            logger.error(f"Error getting user portfolio: {e}")
            return PortfolioResponse(
                success=False,
                error_message=str(e),
                timestamp=str(int(time.time()))
            )
    
    async def GetGeneralAnalysis(self, request, context):
        """获取用户总体分析"""
        try:
            logger.info(f"Getting general analysis for user: {request.user_id}")
            
            # 使用核心分析服务
            result = await self.analysis_service.analyze_general_portfolio(
                request.user_id, 
                allow_empty_portfolio=False
            )
            
            return BaseResponse(
                success=result.success,
                message=result.analysis_summary,
                timestamp=str(result.timestamp),
                error_message=result.error_message or ""
            )
            
        except Exception as e:
            logger.error(f"Error getting general analysis: {e}")
            return BaseResponse(
                success=False,
                message="",
                timestamp=str(int(time.time())),
                error_message=str(e)
            )
    
    async def GetRecommendationsPreview(self, request, context):
        """获取推荐预览"""
        try:
            logger.info(f"Getting recommendations preview for user: {request.user_id}")
            
            # 获取用户数据用于推荐生成
            portfolio = await self.user_data_service.get_user_portfolio(request.user_id)
            if not portfolio:
                return RecommendationsPreviewResponse(
                    success=False,
                    error_message=f"User portfolio not found: {request.user_id}",
                    timestamp=str(int(time.time()))
                )
            
            # 使用多代理系统生成推荐
            multi_agent_response = await self.multi_agent_system.analyze_portfolio_comprehensive(
                portfolio, force_fresh=request.force_fresh
            )
            
            if not multi_agent_response.analyses:
                return RecommendationsPreviewResponse(
                    recommendations=MultiAgentRecommendations(
                        user_id=request.user_id,
                        analyses=[],
                        overall_assessment=multi_agent_response.overall_assessment or "No recommendations available",
                        timestamp=str(int(time.time()))
                    ),
                    success=True,
                    timestamp=str(int(time.time()))
                )
            
            # 转换为gRPC格式
            grpc_analyses = []
            for analysis in multi_agent_response.analyses:
                grpc_recommendations = []
                if hasattr(analysis, 'recommendations') and analysis.recommendations:
                    for rec in analysis.recommendations:
                        grpc_rec = Recommendation(
                            recommendation_id=getattr(rec, 'recommendation_id', f"{request.user_id}_{analysis.agent_name}_{len(grpc_recommendations)}"),
                            title=rec.title,
                            description=rec.description,
                            asset_type=getattr(rec, 'asset_type', analysis.asset_type),
                            potential_gain=float(rec.potential_gain),
                            agent_name=analysis.agent_name,
                            priority=getattr(rec, 'priority', 1)
                        )
                        grpc_recommendations.append(grpc_rec)
                
                grpc_analysis = AgentAnalysis(
                    agent_name=analysis.agent_name,
                    asset_type=analysis.asset_type,
                    findings=analysis.findings,
                    recommendations=grpc_recommendations
                )
                grpc_analyses.append(grpc_analysis)
            
            multi_agent_grpc = MultiAgentRecommendations(
                user_id=request.user_id,
                analyses=grpc_analyses,
                overall_assessment=multi_agent_response.overall_assessment or "",
                timestamp=str(int(time.time()))
            )
            
            return RecommendationsPreviewResponse(
                recommendations=multi_agent_grpc,
                success=True,
                timestamp=str(int(time.time()))
            )
            
        except Exception as e:
            logger.error(f"Error getting recommendations preview: {e}")
            return RecommendationsPreviewResponse(
                success=False,
                error_message=str(e),
                timestamp=str(int(time.time()))
            )
    
    async def SubmitRecommendationFeedback(self, request, context):
        """提交推荐反馈"""
        try:
            logger.info(f"Submitting feedback for recommendation: {request.recommendation_id}")
            
            # 创建反馈请求对象
            from app.models.recommendations import RecommendationFeedbackRequest, RecommendationStatus, RejectionReason
            
            status = RecommendationStatus(request.status)
            rejection_reason = None
            if request.rejection_reason:
                rejection_reason = RejectionReason(request.rejection_reason)
            
            feedback_req = RecommendationFeedbackRequest(
                user_id=request.user_id,
                recommendation_id=request.recommendation_id,
                status=status,
                rejection_reason=rejection_reason,
                rejection_detail=request.rejection_detail if request.rejection_detail else None
            )
            
            # 使用反馈服务保存
            success = await self.feedback_service.save_recommendation_feedback(feedback_req)
            
            return FeedbackResponse(
                success=success,
                message="Feedback submitted successfully" if success else "Failed to submit feedback",
                timestamp=str(int(time.time())),
                error_message="" if success else "Failed to save feedback"
            )
            
        except Exception as e:
            logger.error(f"Error submitting recommendation feedback: {e}")
            return FeedbackResponse(
                success=False,
                message="",
                timestamp=str(int(time.time())),
                error_message=str(e)
            )
    
    async def GetComprehensiveAnalysis(self, request, context):
        """获取综合分析"""
        try:
            logger.info(f"Getting comprehensive analysis for user: {request.user_id}")
            
            # 使用推荐服务获取综合分析
            result = await self.recommendation_service.generate_comprehensive_analysis(
                request.user_id,
                list(request.accepted_recommendation_ids)
            )
            
            return ComprehensiveAnalysisResponse(
                user_id=request.user_id,
                comprehensive_summary=result.get('comprehensive_summary', ''),
                initial_assets=float(result.get('initial_assets', 0)),
                predicted_assets=float(result.get('predicted_assets', 0)),
                timestamp=str(int(time.time())),
                success=result.get('success', True),
                error_message=result.get('error_message', '')
            )
            
        except Exception as e:
            logger.error(f"Error getting comprehensive analysis: {e}")
            return ComprehensiveAnalysisResponse(
                user_id=request.user_id,
                comprehensive_summary="",
                initial_assets=0.0,
                predicted_assets=0.0,
                timestamp=str(int(time.time())),
                success=False,
                error_message=str(e)
            )
    
    async def GetVisualizationData(self, request, context):
        """获取可视化数据"""
        try:
            logger.info(f"Getting visualization data for user: {request.user_id}, type: {request.chart_type}")
            
            # 获取可视化数据
            if request.chart_type == "pie":
                viz_data = await self.visualization_service.generate_pie_chart_data(request.user_id)
            elif request.chart_type == "bar":
                viz_data = await self.visualization_service.generate_bar_chart_data(request.user_id)
            else:
                raise ValueError(f"Unsupported chart type: {request.chart_type}")
            
            # 转换为gRPC格式
            data_map = {}
            if 'asset_breakdown' in viz_data:
                data_map = {k: float(v) for k, v in viz_data['asset_breakdown'].items()}
            
            visualization_data = VisualizationData(
                chart_type=request.chart_type,
                data=data_map,
                total_value=float(viz_data.get('total_value', 0)),
                timestamp=str(int(time.time()))
            )
            
            return VisualizationResponse(
                data=visualization_data,
                success=True,
                timestamp=str(int(time.time()))
            )
            
        except Exception as e:
            logger.error(f"Error getting visualization data: {e}")
            return VisualizationResponse(
                success=False,
                error_message=str(e),
                timestamp=str(int(time.time()))
            )
    
    async def GetUserTasks(self, request, context):
        """获取用户任务"""
        try:
            logger.info(f"Getting tasks for user: {request.user_id}, period: {request.time_period}")
            
            # 获取用户任务
            tasks_data = await self.task_service.get_user_tasks(
                request.user_id, 
                time_period=request.time_period
            )
            
            # 转换为gRPC格式
            grpc_tasks = []
            for task_data in tasks_data.get('tasks', []):
                grpc_task = Task(
                    task_id=task_data.get('task_id', ''),
                    title=task_data.get('title', ''),
                    description=task_data.get('description', ''),
                    due_date=task_data.get('due_date', ''),
                    completion_reward=float(task_data.get('completion_reward', 0)),
                    status=task_data.get('status', 'pending')
                )
                grpc_tasks.append(grpc_task)
            
            return TasksResponse(
                tasks=grpc_tasks,
                success=True,
                timestamp=str(int(time.time()))
            )
            
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return TasksResponse(
                tasks=[],
                success=False,
                error_message=str(e),
                timestamp=str(int(time.time()))
            )
    
    async def FinalizeSession(self, request, context):
        """完成会话"""
        try:
            logger.info(f"Finalizing session for user: {request.user_id}")
            
            # 转换反馈数据
            feedback_dict = {}
            for rec_id, feedback_data in request.feedback.items():
                feedback_dict[rec_id] = {
                    'title': feedback_data.title,
                    'status': feedback_data.status,
                    'rejection_reason': feedback_data.rejection_reason
                }
            
            # 构建会话数据
            session_data = {
                'user_id': request.user_id,
                'feedback': feedback_dict,
                'session_type': request.session_type,
                'input_data': json.loads(request.input_data) if request.input_data else {},
                'ai_response': json.loads(request.ai_response) if request.ai_response else {},
                'processing_time_ms': request.processing_time_ms
            }
            
            # 保存会话
            session_id = await self.feedback_service.save_recommendation_session(
                request.user_id, session_data
            )
            
            success = bool(session_id)
            return BaseResponse(
                success=success,
                message=f"Session finalized successfully: {session_id}" if success else "Failed to finalize session",
                timestamp=str(int(time.time())),
                error_message="" if success else "Failed to save session"
            )
            
        except Exception as e:
            logger.error(f"Error finalizing session: {e}")
            return BaseResponse(
                success=False,
                message="",
                timestamp=str(int(time.time())),
                error_message=str(e)
            )


def _run_async_servicer_method(async_method, request, context):
    """运行异步服务器方法的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_method(request, context))
    finally:
        loop.close()


class SyncSavingAdvisorService(SavingAdvisorServiceServicer):
    """同步包装的gRPC服务"""
    
    def __init__(self):
        self.async_service = SavingAdvisorServiceImpl()
    
    def HealthCheck(self, request, context):
        return _run_async_servicer_method(self.async_service.HealthCheck, request, context)
    
    def GetUserPortfolio(self, request, context):
        return _run_async_servicer_method(self.async_service.GetUserPortfolio, request, context)
    
    def GetGeneralAnalysis(self, request, context):
        return _run_async_servicer_method(self.async_service.GetGeneralAnalysis, request, context)
    
    def GetRecommendationsPreview(self, request, context):
        return _run_async_servicer_method(self.async_service.GetRecommendationsPreview, request, context)
    
    def SubmitRecommendationFeedback(self, request, context):
        return _run_async_servicer_method(self.async_service.SubmitRecommendationFeedback, request, context)
    
    def GetComprehensiveAnalysis(self, request, context):
        return _run_async_servicer_method(self.async_service.GetComprehensiveAnalysis, request, context)
    
    def GetVisualizationData(self, request, context):
        return _run_async_servicer_method(self.async_service.GetVisualizationData, request, context)
    
    def GetUserTasks(self, request, context):
        return _run_async_servicer_method(self.async_service.GetUserTasks, request, context)
    
    def FinalizeSession(self, request, context):
        return _run_async_servicer_method(self.async_service.FinalizeSession, request, context)
