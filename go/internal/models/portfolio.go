package models

import (
	"time"
)

// Asset assetinfo，对应Pythonversion Assetmodel
type Asset struct {
	AssetType        string  `json:"asset_type" firestore:"asset_type"`
	CurrentValue     float64 `json:"current_value" firestore:"current_value"`
	TargetAllocation float64 `json:"target_allocation" firestore:"target_allocation"`
	LastUpdated      string  `json:"last_updated" firestore:"last_updated"` // 存储为字符串，andPython兼容
}

// FirestorePortfolioData Pythonbackend在Firestore中实际存储 data结构
type FirestorePortfolioData struct {
	UserID      string                 `json:"user_id" firestore:"user_id"`
	Points      map[string]interface{} `json:"points" firestore:"points"`
	Earnings    map[string]interface{} `json:"earnings" firestore:"earnings"`
	Items       map[string]interface{} `json:"items" firestore:"items"`
	Giga        map[string]interface{} `json:"giga" firestore:"giga"`
	Stablecoin  map[string]interface{} `json:"stablecoin" firestore:"stablecoin"`
	LastUpdated string                 `json:"last_updated" firestore:"last_updated"`
	DataVersion string                 `json:"data_version" firestore:"data_version"`
}

// Portfolio userportfolio，对应Pythonversion UserPortfoliomodel
type Portfolio struct {
	UserID      string  `json:"user_id"`
	Assets      []Asset `json:"assets"`
	TotalAssets float64 `json:"total_assets"`
	LastUpdated string  `json:"last_updated"`
}

// ToPortfolio 将Firestoredataconvert为Portfolioobject
func (fpd *FirestorePortfolioData) ToPortfolio() *Portfolio {
	var assets []Asset
	var totalAssets float64

	// assettypemap，andPythonbackend保持一致
	assetMap := map[string]string{
		"points":     "Points",
		"earnings":   "Earnings",
		"items":      "Items",
		"giga":       "Giga",
		"stablecoin": "Stablecoin",
	}

	// get各classassetdata
	assetData := map[string]map[string]interface{}{
		"points":     fpd.Points,
		"earnings":   fpd.Earnings,
		"items":      fpd.Items,
		"giga":       fpd.Giga,
		"stablecoin": fpd.Stablecoin,
	}

	for key, assetTypeName := range assetMap {
		data := assetData[key]
		if data == nil {
			data = make(map[string]interface{})
		}

		// getestimated_value，默认为0
		estimatedValue := float64(0)
		if val, ok := data["estimated_value"]; ok {
			if floatVal, ok := val.(float64); ok {
				estimatedValue = floatVal
			}
		}

		assets = append(assets, Asset{
			AssetType:        assetTypeName,
			CurrentValue:     estimatedValue,
			TargetAllocation: 0, // Pythonbackenddata中没有thisfield
			LastUpdated:      fpd.LastUpdated,
		})

		totalAssets += estimatedValue
	}

	return &Portfolio{
		UserID:      fpd.UserID,
		Assets:      assets,
		TotalAssets: totalAssets,
		LastUpdated: fpd.LastUpdated,
	}
}

// GetLastUpdatedTime 将字符串timeconvert为time.Time
func (p *Portfolio) GetLastUpdatedTime() time.Time {
	if p.LastUpdated == "" {
		return time.Now()
	}

	// tryparseISOtime字符串
	if t, err := time.Parse(time.RFC3339, p.LastUpdated); err == nil {
		return t
	}

	// tryparse其他常见格式
	if t, err := time.Parse("2006-01-02T15:04:05.000000", p.LastUpdated); err == nil {
		return t
	}

	// if都fail，returncurrenttime
	return time.Now()
}

// GetLastUpdatedTime 将字符串timeconvert为time.Time
func (a *Asset) GetLastUpdatedTime() time.Time {
	if a.LastUpdated == "" {
		return time.Now()
	}

	// tryparseISOtime字符串
	if t, err := time.Parse(time.RFC3339, a.LastUpdated); err == nil {
		return t
	}

	// tryparse其他常见格式
	if t, err := time.Parse("2006-01-02T15:04:05.000000", a.LastUpdated); err == nil {
		return t
	}

	// if都fail，returncurrenttime
	return time.Now()
}

// VisualizationData 可视化data
type VisualizationData struct {
	ChartType      string             `json:"chart_type"`
	AssetBreakdown map[string]float64 `json:"asset_breakdown"`
	TotalValue     float64            `json:"total_value"`
	Timestamp      string             `json:"timestamp"`
}
