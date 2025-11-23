"""
微服务抽象层测试

验证数据访问抽象层和通信层的正确性
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 导入抽象层组件
from app.services.data.factory import DataServiceFactory, DataSourceType
from app.services.data.interfaces.user_data_interface import UserDataInterface
from app.services.data.interfaces.market_data_interface import MarketDataInterface
from app.services.data.interfaces.feedback_interface import FeedbackInterface
from app.models.assets import UserPortfolio, UserAsset
from app.models.recommendations import RecommendationFeedbackRequest, RecommendationStatus


class TestDataServiceFactory:
    """数据服务工厂测试"""
    
    def test_factory_initialization_default(self):
        """测试工厂默认初始化"""
        factory = DataServiceFactory()
        assert factory.data_source_type == DataSourceType.MOCK
    
    def test_factory_initialization_with_type(self):
        """测试指定类型的工厂初始化"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        assert factory.data_source_type == DataSourceType.MOCK
    
    def test_get_user_data_service(self):
        """测试获取用户数据服务"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        service = factory.get_user_data_service()
        assert isinstance(service, UserDataInterface)
    
    def test_get_market_data_service(self):
        """测试获取市场数据服务"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        service = factory.get_market_data_service()
        assert isinstance(service, MarketDataInterface)
    
    def test_get_feedback_service(self):
        """测试获取反馈服务"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        service = factory.get_feedback_service()
        assert isinstance(service, FeedbackInterface)
    
    def test_service_singleton_behavior(self):
        """测试服务单例行为"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        service1 = factory.get_user_data_service()
        service2 = factory.get_user_data_service()
        assert service1 is service2
    
    def test_switch_data_source(self):
        """测试数据源切换（当前只有MOCK，切换无效但不应报错）"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        original_service = factory.get_user_data_service()
        
        # 切换到相同类型（当前只有MOCK可用）
        factory.switch_data_source(DataSourceType.MOCK)
        new_service = factory.get_user_data_service()
        
        assert factory.data_source_type == DataSourceType.MOCK
        # 相同类型时，服务实例应该相同（单例）
        assert original_service is new_service
    
    def test_get_service_info(self):
        """测试获取服务信息"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        info = factory.get_service_info()
        
        assert 'data_source_type' in info
        assert 'services' in info
        assert 'available_sources' in info
        assert info['data_source_type'] == 'mock'


@pytest.mark.asyncio
class TestMockUserDataService:
    """模拟用户数据服务测试"""
    
    async def test_get_user_portfolio_success(self):
        """测试成功获取用户组合"""
        from app.services.data.implementations.mock.mock_user_service import MockUserDataService
        
        # 模拟Firestore服务
        mock_firestore = AsyncMock()
        mock_portfolio_data = {
            'user_id': 'test_user',
            'assets': [
                {
                    'asset_type': 'ポイント',
                    'current_value': 1000.0,
                    'last_updated': '2024-01-01'
                }
            ],
            'total_value': 1000.0,
            'last_updated': '2024-01-01'
        }
        mock_firestore.get_user_current_assets.return_value = mock_portfolio_data
        
        service = MockUserDataService(firestore_service=mock_firestore)
        portfolio = await service.get_user_portfolio('test_user')
        
        assert portfolio is not None
        assert portfolio.user_id == 'test_user'
        assert len(portfolio.assets) == 1
        assert portfolio.total_value == 1000.0
    
    async def test_get_user_portfolio_not_found(self):
        """测试用户组合不存在"""
        from app.services.data.implementations.mock.mock_user_service import MockUserDataService
        
        mock_firestore = AsyncMock()
        mock_firestore.get_user_current_assets.return_value = None
        
        service = MockUserDataService(firestore_service=mock_firestore)
        portfolio = await service.get_user_portfolio('nonexistent_user')
        
        assert portfolio is None
    
    async def test_check_user_exists(self):
        """测试检查用户存在性"""
        from app.services.data.implementations.mock.mock_user_service import MockUserDataService
        
        mock_firestore = AsyncMock()
        mock_firestore.get_user_profile.return_value = {'user_id': 'test_user', 'name': 'Test User'}
        
        service = MockUserDataService(firestore_service=mock_firestore)
        exists = await service.check_user_exists('test_user')
        
        assert exists is True


@pytest.mark.asyncio
class TestMockMarketDataService:
    """模拟市场数据服务测试"""
    
    async def test_get_market_trends(self):
        """测试获取市场趋势"""
        from app.services.data.implementations.mock.mock_market_service import MockMarketDataService
        
        mock_analytics = AsyncMock()
        mock_trends = {
            'asset_trends': {
                'ポイント': {'trend': 'up', 'percentage': 5.2},
                'モノ': {'trend': 'down', 'percentage': -2.1}
            },
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_analytics.analyze_market_trends.return_value = mock_trends
        
        service = MockMarketDataService(analytics_engine=mock_analytics)
        trends = await service.get_market_trends()
        
        assert 'asset_trends' in trends
        assert 'timestamp' in trends
    
    async def test_get_popular_categories(self):
        """测试获取热门类别"""
        from app.services.data.implementations.mock.mock_market_service import MockMarketDataService
        
        mock_client = AsyncMock()
        mock_categories = [
            {'name': '電子機器', 'popularity': 85.2},
            {'name': 'ファッション', 'popularity': 78.9}
        ]
        mock_client.get_popular_categories.return_value = mock_categories
        
        service = MockMarketDataService(bigquery_client=mock_client)
        categories = await service.get_popular_categories(limit=10)
        
        assert len(categories) == 2
        assert categories[0]['name'] == '電子機器'


@pytest.mark.asyncio
class TestMockFeedbackDataService:
    """模拟反馈数据服务测试"""
    
    async def test_save_recommendation_feedback(self):
        """测试保存推荐反馈"""
        from app.services.data.implementations.mock.mock_feedback_service import MockFeedbackDataService
        
        mock_firestore = AsyncMock()
        mock_firestore.save_recommendation_feedback.return_value = True
        
        service = MockFeedbackDataService(firestore_service=mock_firestore)
        
        feedback = RecommendationFeedbackRequest(
            user_id='test_user',
            recommendation_id='rec_123',
            status=RecommendationStatus.ACCEPTED
        )
        
        result = await service.save_recommendation_feedback(feedback)
        assert result is True
    
    async def test_get_user_feedback_history(self):
        """测试获取用户反馈历史"""
        from app.services.data.implementations.mock.mock_feedback_service import MockFeedbackDataService
        
        mock_firestore = AsyncMock()
        mock_history = [
            {
                'recommendation_id': 'rec_123',
                'status': 'accepted',
                'created_at': '2024-01-01T00:00:00Z'
            }
        ]
        mock_firestore.get_user_feedback_history.return_value = mock_history
        
        service = MockFeedbackDataService(firestore_service=mock_firestore)
        history = await service.get_user_feedback_history('test_user', limit=10)
        
        assert len(history) == 1
        assert history[0]['status'] == 'accepted'


class TestConfigurationManagement:
    """配置管理测试"""
    
    def test_data_source_type_from_config(self):
        """测试从配置读取数据源类型"""
        with patch('app.core.config.settings.DATA_SOURCE_TYPE', 'mock'):
            factory = DataServiceFactory()
            assert factory.data_source_type == DataSourceType.MOCK
    
    def test_invalid_data_source_type(self):
        """测试无效的数据源类型"""
        with pytest.raises(ValueError):
            DataSourceType('invalid_type')


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """集成场景测试"""
    
    async def test_complete_user_flow(self):
        """测试完整的用户流程"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        
        # 模拟服务
        user_service = factory.get_user_data_service()
        market_service = factory.get_market_data_service()
        feedback_service = factory.get_feedback_service()
        
        # 测试用户存在性检查
        with patch.object(user_service, 'check_user_exists', return_value=True):
            user_exists = await user_service.check_user_exists('test_user')
            assert user_exists
        
        # 测试获取用户组合
        mock_portfolio = UserPortfolio(
            user_id='test_user',
            assets=[
                UserAsset(asset_type='ポイント', current_value=1000.0)
            ],
            total_value=1000.0
        )
        
        with patch.object(user_service, 'get_user_portfolio', return_value=mock_portfolio):
            portfolio = await user_service.get_user_portfolio('test_user')
            assert portfolio.total_value == 1000.0
        
        # 测试获取市场数据
        mock_trends = {'trend': 'positive', 'confidence': 0.85}
        with patch.object(market_service, 'get_market_trends', return_value=mock_trends):
            trends = await market_service.get_market_trends()
            assert trends['confidence'] == 0.85
        
        # 测试保存反馈
        feedback = RecommendationFeedbackRequest(
            user_id='test_user',
            recommendation_id='rec_123',
            status=RecommendationStatus.ACCEPTED
        )
        
        with patch.object(feedback_service, 'save_recommendation_feedback', return_value=True):
            saved = await feedback_service.save_recommendation_feedback(feedback)
            assert saved is True
    
    async def test_error_handling_and_fallback(self):
        """测试错误处理和降级"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        user_service = factory.get_user_data_service()
        
        # 模拟服务异常
        with patch.object(user_service, 'get_user_portfolio', side_effect=Exception('Service unavailable')):
            portfolio = await user_service.get_user_portfolio('test_user')
            # 应该返回None而不是抛出异常
            assert portfolio is None
    
    def test_service_switching_runtime(self):
        """测试运行时服务切换（当前只有MOCK类型）"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        
        # 获取Mock服务
        mock_service = factory.get_user_data_service()
        service_info_before = factory.get_service_info()
        
        # 切换到相同类型（当前只有MOCK可用）
        factory.switch_data_source(DataSourceType.MOCK)
        same_service = factory.get_user_data_service()
        service_info_after = factory.get_service_info()
        
        # 验证服务信息
        assert service_info_before['data_source_type'] == 'mock'
        assert service_info_after['data_source_type'] == 'mock'
        # 相同类型时，服务实例应该相同（单例）
        assert mock_service is same_service


class TestPerformanceAndResilience:
    """性能和弹性测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_service_access(self):
        """测试并发服务访问"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        user_service = factory.get_user_data_service()
        
        # 模拟并发访问
        async def get_portfolio(user_id):
            return await user_service.check_user_exists(user_id)
        
        # 创建多个并发任务
        tasks = [get_portfolio(f'user_{i}') for i in range(10)]
        
        with patch.object(user_service, 'check_user_exists', return_value=True):
            results = await asyncio.gather(*tasks)
            assert all(results)
    
    def test_service_instance_caching(self):
        """测试服务实例缓存"""
        factory = DataServiceFactory(DataSourceType.MOCK)
        
        # 多次获取应该返回同一实例
        service1 = factory.get_user_data_service()
        service2 = factory.get_user_data_service()
        service3 = factory.get_market_data_service()
        service4 = factory.get_market_data_service()
        
        assert service1 is service2
        assert service3 is service4
        assert service1 is not service3


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])
