/**
 * フロントエンド設定ファイル
 * 
 * 異なる環境の設定切り替えをサポート
 */

// 環境検出
const getEnvironment = () => {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'development';
    }
    return 'production';
};

// 基礎設定
const baseConfig = {
    environment: getEnvironment(),
    debug: getEnvironment() === 'development',
    
    // API設定
    api: {
        timeout: 30000,
        retryAttempts: 3,
        retryDelay: 1000
    },
    
    // ログ設定
    logging: {
        enabled: true,
        level: getEnvironment() === 'development' ? 'debug' : 'info',
        enablePerformanceTracking: true
    },
    
    // 機能フラグ
    features: {
        grpcWebEnabled: false, // 現在はプレースホルダーのみ、実際のgRPC-Web機能は未実装
        restApiEnabled: true,
        protocolSwitching: true, // 実行時にプロトコル切り替えを許可するかどうか
        performanceMonitoring: true
    }
};

// 開発環境設定
const developmentConfig = {
    ...baseConfig,
    
    communication: {
        protocol: 'rest', // 'rest' | 'grpc-web'
        endpoints: {
            rest: {
                // Python後端 (FastAPI)
                python: 'http://localhost:8080/api/v1',
                // Go後端 (HTTP Gateway)  
                go: 'http://localhost:8081/api/v1',
                // 默认使用Python后端（gRPC REST Gateway）
                baseUrl: 'http://localhost:8080/api/v1'
            },
            grpcWeb: {
                // Python gRPC
                python: 'http://localhost:50051',
                // Go gRPC  
                go: 'http://localhost:50052',
                // 默认使用Python gRPC
                baseUrl: 'http://localhost:50051',
                timeout: 10000
            }
        },
        enableLogging: true,
        enableMetrics: true
    },
    
    // 開発環境特有の機能
    dev: {
        showDebugInfo: true,
        mockDelay: 0, // ネットワーク遅延をシミュレート（ミリ秒）
        enableHotReload: true
    }
};

// 本番環境設定
const productionConfig = {
    ...baseConfig,
    
    communication: {
        protocol: 'grpc-web', // 本番環境ではgRPC-Webを優先
        endpoints: {
            rest: {
                baseUrl: '/api/v1' // 本番環境ではAPI Gateway経由でアクセス
            },
            grpcWeb: {
                baseUrl: '/grpc-web', // 本番環境ではAPI Gateway経由でアクセス
                timeout: 15000
            }
        },
        enableLogging: false, // 本番環境では詳細ログを無効化
        enableMetrics: true
    },
    
    // 本番環境の最適化
    optimization: {
        enableCaching: true,
        cacheTimeout: 300000, // 5分
        enableCompression: true
    }
};

// Mercari統合設定（将来使用）
const mercariIntegrationConfig = {
    // Mercariメインアプリケーションに統合された際の設定
    communication: {
        protocol: 'grpc-web', // Mercari環境ではgRPCを強制
        endpoints: {
            grpcWeb: {
                baseUrl: '/mercari-grpc', // Mercari内部のgRPCサービスアドレス
                timeout: 20000,
                authentication: {
                    enabled: true,
                    tokenHeader: 'Authorization'
                }
            },
            rest: {
                baseUrl: '/mercari-rest', // Mercari内部のRESTサービスアドレス（予備）
                authentication: {
                    enabled: true,
                    tokenHeader: 'Authorization'
                }
            }
        },
        enableLogging: false,
        enableMetrics: true
    },
    
    // Mercari特有の機能
    mercari: {
        serviceRegistry: '/mercari/services',
        healthCheck: '/mercari/health',
        configEndpoint: '/mercari/config'
    }
};

// 環境に応じて設定を選択
const getConfig = () => {
    const env = getEnvironment();
    
    switch (env) {
        case 'development':
            return developmentConfig;
        case 'production':
            return productionConfig;
        default:
            return developmentConfig;
    }
};

// 設定マネージャー
class ConfigManager {
    constructor() {
        this.config = getConfig();
        this.listeners = [];
        
        // localStorageからユーザー設定を読み込む
        this.loadUserPreferences();
        
        console.log('ConfigManager initialized for environment:', this.config.environment);
    }
    
    /**
     * 設定値を取得
     */
    get(path, defaultValue = null) {
        const keys = path.split('.');
        let value = this.config;
        
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }
        
        return value;
    }
    
    /**
     * 設定値を設定（実行時のみ）
     */
    set(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let target = this.config;
        
        for (const key of keys) {
            if (!(key in target)) {
                target[key] = {};
            }
            target = target[key];
        }
        
        const oldValue = target[lastKey];
        target[lastKey] = value;
        
        // リスナーに通知
        this.notifyListeners(path, value, oldValue);
        
        // localStorageに保存
        this.saveUserPreferences();
    }
    
    /**
     * 設定変更リスナーを追加
     */
    onChange(path, callback) {
        this.listeners.push({ path, callback });
    }
    
    /**
     * リスナーに通知
     */
    notifyListeners(path, newValue, oldValue) {
        this.listeners.forEach(listener => {
            if (listener.path === path || path.startsWith(listener.path + '.')) {
                listener.callback(newValue, oldValue, path);
            }
        });
    }
    
    /**
     * ユーザー設定を読み込む
     */
    loadUserPreferences() {
        try {
            const saved = localStorage.getItem('savingAdvisor.config');
            if (saved) {
                const preferences = JSON.parse(saved);
                
                // ユーザー設定を現在の設定にマージ
                if (preferences.communication?.protocol) {
                    this.config.communication.protocol = preferences.communication.protocol;
                }
                
                if (preferences.features) {
                    Object.assign(this.config.features, preferences.features);
                }
            }
        } catch (error) {
            console.warn('Failed to load user preferences:', error);
        }
    }
    
    /**
     * ユーザー設定を保存
     */
    saveUserPreferences() {
        try {
            const preferences = {
                communication: {
                    protocol: this.config.communication.protocol
                },
                features: this.config.features
            };
            
            localStorage.setItem('savingAdvisor.config', JSON.stringify(preferences));
        } catch (error) {
            console.warn('Failed to save user preferences:', error);
        }
    }
    
    /**
     * デフォルト設定にリセット
     */
    reset() {
        this.config = getConfig();
        localStorage.removeItem('savingAdvisor.config');
        console.log('Configuration reset to defaults');
    }
    
    /**
     * 完全な設定情報を取得
     */
    getFullConfig() {
        return { ...this.config };
    }
    
    /**
     * 機能が有効かどうかをチェック
     */
    isFeatureEnabled(feature) {
        return this.get(`features.${feature}`, false);
    }
    
    /**
     * 通信プロトコルを取得
     */
    getProtocol() {
        return this.get('communication.protocol', 'rest');
    }
    
    /**
     * 通信プロトコルを設定
     */
    setProtocol(protocol) {
        if (protocol !== 'rest' && protocol !== 'grpc-web') {
            throw new Error(`Invalid protocol: ${protocol}`);
        }
        
        this.set('communication.protocol', protocol);
        console.log(`Communication protocol switched to: ${protocol}`);
    }
    
    /**
     * 環境情報を取得
     */
    getEnvironmentInfo() {
        return {
            environment: this.config.environment,
            debug: this.config.debug,
            protocol: this.getProtocol(),
            features: this.config.features
        };
    }
}

// グローバル設定マネージャーインスタンスを作成
const configManager = new ConfigManager();

// 設定とマネージャーをエクスポート
window.SavingAdvisorConfig = {
    manager: configManager,
    get: (path, defaultValue) => configManager.get(path, defaultValue),
    set: (path, value) => configManager.set(path, value),
    isFeatureEnabled: (feature) => configManager.isFeatureEnabled(feature),
    getProtocol: () => configManager.getProtocol(),
    setProtocol: (protocol) => configManager.setProtocol(protocol),
    getEnvironmentInfo: () => configManager.getEnvironmentInfo()
};

console.log('Saving Advisor configuration loaded:', configManager.getEnvironmentInfo());
