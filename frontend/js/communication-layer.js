/**
 * フロントエンド通信抽象レイヤー
 * 
 * REST APIとgRPC-Webの設定可能な切り替えをサポート
 * 将来のMercari本体アプリケーションとの統合準備
 */

class CommunicationLayer {
    constructor(config = {}) {
        this.config = {
            protocol: config.protocol || 'rest', // 'rest' | 'grpc-web'
            endpoints: {
                rest: {
                    baseUrl: config.restBaseUrl || '/api/v1'
                },
                grpcWeb: {
                    baseUrl: config.grpcWebBaseUrl || '/grpc-web',
                    // gRPC-Webクライアントはここで初期化されます
                    client: null
                }
            },
            // デバッグとパフォーマンス監視
            enableLogging: config.enableLogging || true,
            timeout: config.timeout || 30000
        };

        this.initialized = false;
        this.performanceMetrics = {
            restCalls: [],
            grpcCalls: []
        };

        console.log(`CommunicationLayer initialized with protocol: ${this.config.protocol}`);
    }

    /**
     * 通信レイヤーを初期化
     */
    async initialize() {
        if (this.initialized) return;

        try {
            if (this.config.protocol === 'grpc-web') {
                await this.initializeGrpcWeb();
            }
            
            this.initialized = true;
            console.log(`CommunicationLayer initialized successfully`);
        } catch (error) {
            console.error('Failed to initialize CommunicationLayer:', error);
            // REST APIへフォールバック
            this.config.protocol = 'rest';
            this.initialized = true;
            console.warn('Falling back to REST API');
        }
    }

    /**
     * gRPC-Webクライアントを初期化
     */
    async initializeGrpcWeb() {
        // TODO: gRPC-Webプロキシの設定完了後に実装
        // const { SavingAdvisorServiceClient } = require('./generated/saving_advisor_grpc_web_pb');
        // this.config.endpoints.grpcWeb.client = new SavingAdvisorServiceClient(
        //     this.config.endpoints.grpcWeb.baseUrl
        // );
        
        console.log('gRPC-Web client initialized (placeholder)');
    }

    /**
     * 通信プロトコルを切り替え
     */
    async switchProtocol(newProtocol) {
        if (newProtocol === this.config.protocol) return;

        console.log(`Switching protocol from ${this.config.protocol} to ${newProtocol}`);
        this.config.protocol = newProtocol;
        this.initialized = false;
        await this.initialize();
    }

    /**
     * ユーザーポートフォリオを取得
     */
    async getUserPortfolio(userId) {
        return this.config.protocol === 'grpc-web' 
            ? this.grpcGetUserPortfolio(userId)
            : this.restGetUserPortfolio(userId);
    }

    /**
     * ユーザー分析を取得
     */
    async getUserAnalysis(userId) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcGetUserAnalysis(userId)
            : this.restGetUserAnalysis(userId);
    }

    /**
     * 推薦プレビューを取得
     */
    async getRecommendationsPreview(userId, forceFresh = false) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcGetRecommendationsPreview(userId, forceFresh)
            : this.restGetRecommendationsPreview(userId, forceFresh);
    }

    /**
     * 推薦フィードバックを送信
     */
    async submitRecommendationFeedback(feedbackData) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcSubmitFeedback(feedbackData)
            : this.restSubmitFeedback(feedbackData);
    }

    /**
     * 総合分析を取得
     */
    async getComprehensiveAnalysis(userId, acceptedIds) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcGetComprehensiveAnalysis(userId, acceptedIds)
            : this.restGetComprehensiveAnalysis(userId, acceptedIds);
    }

    /**
     * 可視化データを取得
     */
    async getVisualizationData(userId, chartType) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcGetVisualizationData(userId, chartType)
            : this.restGetVisualizationData(userId, chartType);
    }

    /**
     * ユーザーのタスクを取得
     */
    async getUserTasks(userId, acceptedIds, timePeriod = 'monthly') {
        return this.config.protocol === 'grpc-web'
            ? this.grpcGetUserTasks(userId, acceptedIds, timePeriod)
            : this.restGetUserTasks(userId, acceptedIds, timePeriod);
    }

    /**
     * セッションを完了
     */
    async finalizeSession(sessionData) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcFinalizeSession(sessionData)
            : this.restFinalizeSession(sessionData);
    }

    /**
     * 推薦を再生成
     */
    async regenerateRecommendation(payload) {
        return this.config.protocol === 'grpc-web'
            ? this.grpcRegenerateRecommendation(payload)
            : this.restRegenerateRecommendation(payload);
    }

    // ==================== REST API 実装 ====================

    async restGetUserPortfolio(userId) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/assets/portfolio/${userId}`
            );
            this.recordMetric('rest', 'getUserPortfolio', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getUserPortfolio', Date.now() - startTime, false);
            throw error;
        }
    }

    async restGetUserAnalysis(userId) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/analysis/general/${userId}`
            );
            this.recordMetric('rest', 'getUserAnalysis', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getUserAnalysis', Date.now() - startTime, false);
            throw error;
        }
    }

    async restGetRecommendationsPreview(userId, forceFresh) {
        const startTime = Date.now();
        try {
            const url = `${this.config.endpoints.rest.baseUrl}/tasks/recommendations/preview/${userId}`;
            const queryParams = forceFresh ? '?force_fresh=true' : '';
            const response = await this.makeRestCall(url + queryParams);
            this.recordMetric('rest', 'getRecommendationsPreview', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getRecommendationsPreview', Date.now() - startTime, false);
            throw error;
        }
    }

    async restSubmitFeedback(feedbackData) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/recommendations/feedback`,
                'POST',
                feedbackData
            );
            this.recordMetric('rest', 'submitFeedback', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'submitFeedback', Date.now() - startTime, false);
            throw error;
        }
    }

    async restGetComprehensiveAnalysis(userId, acceptedIds) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/tasks/comprehensive/${userId}`,
                'POST',
                { accepted_recommendation_ids: acceptedIds }
            );
            this.recordMetric('rest', 'getComprehensiveAnalysis', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getComprehensiveAnalysis', Date.now() - startTime, false);
            throw error;
        }
    }

    async restGetVisualizationData(userId, chartType) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/visualization/${userId}?chart_type=${chartType}`
            );
            this.recordMetric('rest', 'getVisualizationData', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getVisualizationData', Date.now() - startTime, false);
            throw error;
        }
    }

    async restGetUserTasks(userId, acceptedIds, timePeriod) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/tasks/${timePeriod}/${userId}`,
                'POST',
                { accepted_recommendation_ids: acceptedIds }
            );
            this.recordMetric('rest', 'getUserTasks', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'getUserTasks', Date.now() - startTime, false);
            throw error;
        }
    }

    async restFinalizeSession(sessionData) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/tasks/session/finalize`,
                'POST',
                sessionData
            );
            this.recordMetric('rest', 'finalizeSession', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'finalizeSession', Date.now() - startTime, false);
            throw error;
        }
    }

    async restRegenerateRecommendation(payload) {
        const startTime = Date.now();
        try {
            const response = await this.makeRestCall(
                `${this.config.endpoints.rest.baseUrl}/recommendations/regenerate`,
                'POST',
                payload
            );
            this.recordMetric('rest', 'regenerateRecommendation', Date.now() - startTime, true);
            return response;
        } catch (error) {
            this.recordMetric('rest', 'regenerateRecommendation', Date.now() - startTime, false);
            throw error;
        }
    }

    // ==================== gRPC-Web 実装 ====================

    async grpcGetUserPortfolio(userId) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getUserPortfolio - not implemented yet');
            // 一時的にRESTにフォールバック
            const result = await this.restGetUserPortfolio(userId);
            this.recordMetric('grpc', 'getUserPortfolio', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getUserPortfolio', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcGetUserAnalysis(userId) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getUserAnalysis - not implemented yet');
            const result = await this.restGetUserAnalysis(userId);
            this.recordMetric('grpc', 'getUserAnalysis', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getUserAnalysis', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcGetRecommendationsPreview(userId, forceFresh) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getRecommendationsPreview - not implemented yet');
            const result = await this.restGetRecommendationsPreview(userId, forceFresh);
            this.recordMetric('grpc', 'getRecommendationsPreview', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getRecommendationsPreview', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcSubmitFeedback(feedbackData) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web submitFeedback - not implemented yet');
            const result = await this.restSubmitFeedback(feedbackData);
            this.recordMetric('grpc', 'submitFeedback', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'submitFeedback', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcGetComprehensiveAnalysis(userId, acceptedIds) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getComprehensiveAnalysis - not implemented yet');
            const result = await this.restGetComprehensiveAnalysis(userId, acceptedIds);
            this.recordMetric('grpc', 'getComprehensiveAnalysis', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getComprehensiveAnalysis', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcGetVisualizationData(userId, chartType) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getVisualizationData - not implemented yet');
            const result = await this.restGetVisualizationData(userId, chartType);
            this.recordMetric('grpc', 'getVisualizationData', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getVisualizationData', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcGetUserTasks(userId, acceptedIds, timePeriod) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web getUserTasks - not implemented yet');
            const result = await this.restGetUserTasks(userId, acceptedIds, timePeriod);
            this.recordMetric('grpc', 'getUserTasks', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'getUserTasks', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcFinalizeSession(sessionData) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web finalizeSession - not implemented yet');
            
            // gRPCは文字列形式を期待するため、変換が必要
            const grpcSessionData = {
                ...sessionData,
                input_data: JSON.stringify(sessionData.input_data),
                ai_response: JSON.stringify(sessionData.ai_response)
            };
            
            // 一時的にRESTにフォールバック（フォーマット変換付き）
            const result = await this.restFinalizeSession(sessionData);
            this.recordMetric('grpc', 'finalizeSession', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'finalizeSession', Date.now() - startTime, false);
            throw error;
        }
    }

    async grpcRegenerateRecommendation(payload) {
        const startTime = Date.now();
        try {
            // TODO: gRPC-Web呼び出しを実装
            console.log('gRPC-Web regenerateRecommendation - not implemented yet');
            const result = await this.restRegenerateRecommendation(payload);
            this.recordMetric('grpc', 'regenerateRecommendation', Date.now() - startTime, true);
            return result;
        } catch (error) {
            this.recordMetric('grpc', 'regenerateRecommendation', Date.now() - startTime, false);
            throw error;
        }
    }

    // ==================== ヘルパーメソッド ====================

    async makeRestCall(url, method = 'GET', body = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
            ...(body && { body: JSON.stringify(body) }),
        };

        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`);
        }

        if (response.status === 204) {
            return null;
        }

        return await response.json();
    }

    recordMetric(protocol, method, duration, success) {
        const metric = {
            protocol,
            method,
            duration,
            success,
            timestamp: Date.now()
        };

        if (protocol === 'rest') {
            this.performanceMetrics.restCalls.push(metric);
        } else {
            this.performanceMetrics.grpcCalls.push(metric);
        }

        // 最近100回の呼び出し記録を保持
        if (this.performanceMetrics.restCalls.length > 100) {
            this.performanceMetrics.restCalls = this.performanceMetrics.restCalls.slice(-100);
        }
        if (this.performanceMetrics.grpcCalls.length > 100) {
            this.performanceMetrics.grpcCalls = this.performanceMetrics.grpcCalls.slice(-100);
        }

        if (this.config.enableLogging) {
            console.log(`${protocol.toUpperCase()} ${method}: ${duration}ms (${success ? 'success' : 'failed'})`);
        }
    }

    getPerformanceMetrics() {
        const calculateStats = (calls) => {
            if (calls.length === 0) return null;
            
            const successful = calls.filter(c => c.success);
            const failed = calls.filter(c => !c.success);
            const durations = successful.map(c => c.duration);
            
            return {
                totalCalls: calls.length,
                successfulCalls: successful.length,
                failedCalls: failed.length,
                successRate: (successful.length / calls.length * 100).toFixed(2),
                avgDuration: durations.length > 0 ? (durations.reduce((a, b) => a + b, 0) / durations.length).toFixed(2) : 0,
                minDuration: durations.length > 0 ? Math.min(...durations) : 0,
                maxDuration: durations.length > 0 ? Math.max(...durations) : 0
            };
        };

        return {
            currentProtocol: this.config.protocol,
            rest: calculateStats(this.performanceMetrics.restCalls),
            grpc: calculateStats(this.performanceMetrics.grpcCalls)
        };
    }

    getConfigInfo() {
        return {
            protocol: this.config.protocol,
            initialized: this.initialized,
            endpoints: this.config.endpoints,
            features: {
                grpcWebReady: this.config.endpoints.grpcWeb.client !== null,
                restReady: true,
                switchingSupported: true
            }
        };
    }

    async switchDataSource(source) {
        if (!['mock', 'mercari'].includes(source)) {
            console.error('Invalid data source:', source);
            return;
        }
        try {
            const response = await fetch(`${this.config.endpoints.rest.baseUrl}/debug/switch-data-source`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: source })
            });
            if (!response.ok) {
                throw new Error(`Failed to switch data source: ${response.statusText}`);
            }
            const result = await response.json();
            this.data_source = result.new_config.data_source_type;
            console.log('Successfully switched data source:', result);
            return result.new_config;
        } catch (error) {
            console.error('Error switching data source:', error);
            throw error;
        }
    }

    async getDataSourceStatus() {
        try {
            const response = await fetch(`${this.config.endpoints.rest.baseUrl}/debug/data-source-status`);
            if (!response.ok) {
                throw new Error(`Failed to get data source status: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error getting data source status:', error);
            throw error;
        }
    }
}
