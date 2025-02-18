import os
import sys 
import numpy as np
from dataclasses import dataclass

from sklearn.linear_model import LinearRegression, Ridge, Lasso 
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor

from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

from src.mlproject.exception import CustomException
from src.mlproject.logger import logging
from src.mlproject.utils import save_object, evaluate_models

import mlflow
from urllib.parse import urlparse
import dagshub

dagshub.init(repo_owner='LokeshKumarDas', repo_name='ML_Project', mlflow=True)


@dataclass
class ModelTrainerConfig:
    trained_model_file_path = os.path.join('artifacts', 'model.pkl')
    
class ModelTrainer:
    def __init__(self):
        self.model_trainer_config = ModelTrainerConfig()
    
    def eval_metrics(self, actual, pred):
        
        rmse = np.sqrt(mean_squared_error(actual, pred))
        r2 = r2_score(actual, pred)
        mae = mean_absolute_error(actual, pred)
        
        return rmse, mae, r2
    
    def initiate_model_trainer(self, train_array, test_array):
        try:
            logging.info('Split training and testing input vs output data')
            
            X_train, y_train, X_test, y_test = (
                train_array[:,:-1], 
                train_array[:,-1],
                test_array[:,:-1], 
                test_array[:,-1]
                )
            
            models = {
                'LinearRegression': LinearRegression(),
                'Decision Tree' : DecisionTreeRegressor(),
                'Random Forest Regressor' : RandomForestRegressor(),
                'Gradient Boosting': GradientBoostingRegressor(),
                'Ada-Boost Regressor' : AdaBoostRegressor() ,
                'XGBRegressor' : XGBRegressor()
            }
            
            params = {
                'LinearRegression': {},
                'Decision Tree' : {
                    'criterion':['squared_error', 'friedman_mse', 'absolute_error', 'poisson']
                    },
                'Random Forest Regressor' : {
                    'n_estimators': [8, 16, 32, 64, 128, 256]
                    },
                'Gradient Boosting': {
                    'learning_rate': [0.1, 0.01, 0.05, 0.001],
                    'subsample': [0.6, 0.7, 0.75, 0.8, 0.85, 0.9],
                    'n_estimators': [8, 16, 32, 64, 128, 256]
                    },
                'Ada-Boost Regressor' : {
                    'learning_rate': [0.1, 0.01, 0.05, 0.001],
                    'n_estimators': [8, 16, 32, 64, 128, 256]
                    },
                'XGBRegressor' : {
                    'learning_rate': [0.1, 0.01, 0.05, 0.001],
                    'n_estimators': [8, 16, 32, 64, 128, 256]
                    }
            }
            
            model_report : dict = evaluate_models(
                X_train, y_train, X_test, y_test, models, params
            )
            
            best_model_score = max(sorted(model_report.values()))
            
            best_model_name = list(model_report.keys())[
                list(model_report.values()).index(best_model_score)
            ]
            
            best_model = models[best_model_name]
            
            print(f'best model is {best_model_name}')
            
            # Fix this part of the code
            model_names = list(params.keys())
            actual_model = ''
            for model_name in model_names:
                if best_model_name == model_name:
                    actual_model = model_name

            
            try:
                # Check actual_model value
                print(f"Actual model: {actual_model}")
                print(f"Available model params: {params.keys()}")

                # Access best params for the actual model
                best_params = params[actual_model]
    
            except KeyError as e:
                print(f"KeyError: {e}")
                raise CustomException(f"Model {actual_model} not found in params.", sys)
            
            # mlflow code .....
            
            mlflow.set_registry_uri('https://dagshub.com/LokeshKumarDas/ML_Project.mlflow')
            tracking_url_type_store = urlparse(mlflow.get_tracking_uri()).scheme
            
            with mlflow.start_run():
                predict_qualities = best_model.predict(X_test)
                (rmse, mae, r2) = self.eval_metrics(y_test, predict_qualities)
                
                mlflow.log_param(actual_model, best_params)
                mlflow.log_metric('rmse', rmse)
                mlflow.log_metric('r2 score', r2)
                mlflow.log_metric('mae', mae)
                
                if tracking_url_type_store != 'file':
                    mlflow.sklearn.log_model(best_model, 'model', registered_model_name = actual_model)
                else:
                    mlflow.sklearn.log_model(best_model, 'model')
                
                
            # Saving best model as .pkl file and returning best model with accuracy scores on train and test data
            if best_model_score < 0.65:
                raise CustomException('NO Best Model Found')
            
            logging.info('Best found Model on both training and testing dataset')
            
            save_object(
                file_path=self.model_trainer_config.trained_model_file_path,
                obj = best_model
            )
            
            predicted_train = best_model.predict(X_train)
            predicted_test = best_model.predict(X_test)
            
            score_train = mean_squared_error(y_train, predicted_train)
            score_test = mean_squared_error(y_test, predicted_test)
            
            return (best_model, score_train, score_test)
            
        except Exception as e:
            raise CustomException(e, sys)   
        