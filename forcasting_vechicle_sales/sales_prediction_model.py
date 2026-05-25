import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class CarSalesPredictor:
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.best_model = None
        
    def load_data(self, file_path):
        self.data = pd.read_csv(file_path)
        print(f"数据加载成功，共 {self.data.shape[0]} 条记录，{self.data.shape[1]} 个特征")
        return self.data
    
    def explore_data(self):
        print("\n=== 数据概览 ===")
        print(self.data.describe())
        
        print("\n=== 分类特征分布 ===")
        categorical_cols = ['Manufacturer', 'Vehicle_Type', 'Fuel_Type', 'Transmission', 'Region']
        for col in categorical_cols:
            print(f"\n{col}:")
            print(self.data[col].value_counts())
        
        print("\n=== 销售数据分布 ===")
        plt.figure(figsize=(10, 6))
        sns.histplot(self.data['Sales'], bins=30, kde=True)
        plt.title('Sales Distribution')
        plt.savefig('sales_distribution.png')
        plt.close()
        
        print("\n=== 相关性分析 ===")
        numeric_cols = ['Year', 'Engine_Size', 'Horsepower', 'MPG', 'Price', 'Mileage', 'Age', 'Sales']
        corr_matrix = self.data[numeric_cols].corr()
        plt.figure(figsize=(12, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt='.2f')
        plt.title('Correlation Matrix')
        plt.savefig('correlation_matrix.png')
        plt.close()
        
    def preprocess_data(self):
        X = self.data.drop(['Sales', 'Model'], axis=1)
        y = self.data['Sales']
        
        categorical_features = ['Manufacturer', 'Vehicle_Type', 'Fuel_Type', 'Transmission', 'Region']
        numeric_features = ['Year', 'Engine_Size', 'Horsepower', 'MPG', 'Price', 'Mileage', 'Age']
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), categorical_features)
            ])
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        return X_train, X_test, y_train, y_test
    
    def train_models(self, X_train, y_train):
        models = {
            'Linear Regression': LinearRegression(),
            'Random Forest': RandomForestRegressor(random_state=42),
            'Gradient Boosting': GradientBoostingRegressor(random_state=42)
        }
        
        param_grids = {
            'Linear Regression': {},
            'Random Forest': {
                'regressor__n_estimators': [100, 200],
                'regressor__max_depth': [None, 10, 20],
                'regressor__min_samples_split': [2, 5]
            },
            'Gradient Boosting': {
                'regressor__n_estimators': [100, 200],
                'regressor__learning_rate': [0.01, 0.1],
                'regressor__max_depth': [3, 5]
            }
        }
        
        best_models = {}
        best_scores = {}
        
        for name, model in models.items():
            pipeline = Pipeline([
                ('preprocessor', self.preprocessor),
                ('regressor', model)
            ])
            
            grid_search = GridSearchCV(pipeline, param_grids[name], cv=5, scoring='neg_mean_squared_error', n_jobs=-1)
            grid_search.fit(X_train, y_train)
            
            best_models[name] = grid_search.best_estimator_
            best_scores[name] = -grid_search.best_score_
            print(f"{name} - 最佳MSE: {best_scores[name]:.2f}")
        
        best_model_name = min(best_scores, key=best_scores.get)
        self.best_model = best_models[best_model_name]
        print(f"\n最佳模型: {best_model_name}")
        
        return self.best_model
    
    def evaluate_model(self, X_test, y_test):
        y_pred = self.best_model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        print("\n=== 模型评估结果 ===")
        print(f"MAE: {mae:.2f}")
        print(f"MSE: {mse:.2f}")
        print(f"RMSE: {rmse:.2f}")
        print(f"R2 Score: {r2:.4f}")
        
        plt.figure(figsize=(10, 6))
        plt.scatter(y_test, y_pred, alpha=0.6)
        plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
        plt.xlabel('实际销售额')
        plt.ylabel('预测销售额')
        plt.title('实际vs预测销售额')
        plt.savefig('actual_vs_predicted.png')
        plt.close()
        
        return {'MAE': mae, 'MSE': mse, 'RMSE': rmse, 'R2': r2}
    
    def feature_importance(self):
        if hasattr(self.best_model.named_steps['regressor'], 'feature_importances_'):
            importances = self.best_model.named_steps['regressor'].feature_importances_
            
            cat_features = self.best_model.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out()
            num_features = ['Year', 'Engine_Size', 'Horsepower', 'MPG', 'Price', 'Mileage', 'Age']
            all_features = np.concatenate([num_features, cat_features])
            
            feature_importance_df = pd.DataFrame({
                'Feature': all_features,
                'Importance': importances
            }).sort_values('Importance', ascending=False)
            
            plt.figure(figsize=(12, 8))
            sns.barplot(x='Importance', y='Feature', data=feature_importance_df.head(20))
            plt.title('特征重要性排名')
            plt.savefig('feature_importance.png')
            plt.close()
            
            print("\n=== 特征重要性 ===")
            print(feature_importance_df.head(10))
            
            return feature_importance_df
    
    def save_model(self, file_path='car_sales_model.pkl'):
        joblib.dump(self.best_model, file_path)
        print(f"\n模型已保存到: {file_path}")
    
    def predict(self, new_data):
        if isinstance(new_data, dict):
            new_data = pd.DataFrame([new_data])
        return self.best_model.predict(new_data)
    
    def run(self, data_path='car_sales_data.csv'):
        self.load_data(data_path)
        self.explore_data()
        X_train, X_test, y_train, y_test = self.preprocess_data()
        self.train_models(X_train, y_train)
        metrics = self.evaluate_model(X_test, y_test)
        self.feature_importance()
        self.save_model()
        return metrics

if __name__ == '__main__':
    predictor = CarSalesPredictor()
    predictor.run()