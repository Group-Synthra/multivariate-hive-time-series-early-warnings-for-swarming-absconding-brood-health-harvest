"""
LSTM Network for Swarming Prediction - OPTIMIZED for speed
Lightweight PyTorch implementation with optimizations
"""

import numpy as np
import pandas as pd
from pathlib import Path
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, confusion_matrix)
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Check for GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")
if device.type == 'cpu':
    print("⚠️  WARNING: Running on CPU. Training will be slow!")
    print("   Consider using Google Colab or a machine with GPU")


class LSTMSwarmingModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        # Simplified model for faster training
        self.lstm = nn.LSTM(input_size, 64, 1, batch_first=True, dropout=0.2)  # 1 layer, 64 units
        self.dropout = nn.Dropout(0.2)
        self.fc1 = nn.Linear(64, 32)
        self.fc2 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]
        x = self.relu(self.fc1(last_out))
        x = self.dropout(x)
        x = self.sigmoid(self.fc2(x))
        return x


class LSTMTraining:
    def __init__(self, output_dir=None, figures_dir=None):
        self.output_dir = output_dir or Path(__file__).parent.parent.parent.parent / 'ml' / 'swarming' / 'models'
        self.figures_dir = figures_dir or self.output_dir.parent / 'outputs' / 'swarming' / 'figures'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
    
    def handle_imbalance_with_weights(self, y_train):
        """Use class weights instead of SMOTE (faster)"""
        classes = np.unique(y_train)
        weights = compute_class_weight('balanced', classes=classes, y=y_train)
        class_weight = dict(zip(classes, weights))
        print(f"   Class weights: {class_weight}")
        
        # Convert to tensor for loss function
        weight_tensor = torch.FloatTensor([class_weight[0], class_weight[1]])
        return weight_tensor
    
    def calculate_metrics(self, y_true, y_pred, y_proba):
        """Calculate metrics"""
        return {
            'accuracy': round(accuracy_score(y_true, y_pred), 4),
            'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
            'recall': round(recall_score(y_true, y_pred, zero_division=0), 4),
            'f1_score': round(f1_score(y_true, y_pred, zero_division=0), 4),
            'roc_auc': round(roc_auc_score(y_true, y_proba), 4) if len(np.unique(y_true)) > 1 else 0.5,
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
    
    def train(self, X_train, y_train, X_val, y_val, X_test, y_test, feature_cols=None):
        """Train LSTM model with optimizations"""
        print("\n" + "="*70)
        print("TRAINING LSTM NETWORK (OPTIMIZED FOR SPEED)")
        print("="*70)
        
        start_time = time.time()
        
        # Use subset of data for faster training (50k samples)
        n_samples = len(X_train)
        if n_samples > 50000:
            print(f"\n   Using 50,000 samples from {n_samples} for faster training")
            indices = np.random.choice(n_samples, 50000, replace=False)
            X_train = X_train[indices]
            y_train = y_train[indices]
        
        print(f"\n   Training samples: {len(X_train)}")
        print(f"   Validation samples: {len(X_val)}")
        print(f"   Test samples: {len(X_test)}")
        print(f"   Sequence length: {X_train.shape[1]}")
        print(f"   Features: {X_train.shape[2]}")
        
        # Use class weights instead of SMOTE
        print("\n[1/4] Setting up class weights...")
        class_weights = self.handle_imbalance_with_weights(y_train)
        
        # Convert to tensors (use float32 for efficiency)
        print("\n[2/4] Preparing data loaders...")
        X_train_tensor = torch.FloatTensor(X_train)
        y_train_tensor = torch.FloatTensor(y_train).reshape(-1, 1)
        X_val_tensor = torch.FloatTensor(X_val)
        y_val_tensor = torch.FloatTensor(y_val).reshape(-1, 1)
        X_test_tensor = torch.FloatTensor(X_test)
        y_test_tensor = torch.FloatTensor(y_test).reshape(-1, 1)
        
        # Use larger batch size for faster training
        batch_size = 256  # Increased from 64
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Build model
        input_size = X_train.shape[2]
        print(f"\n[3/4] Building model...")
        print(f"   Input size: {input_size}")
        
        self.model = LSTMSwarmingModel(input_size=input_size).to(device)
        
        # Loss with class weights
        criterion = nn.BCEWithLogitsLoss(pos_weight=class_weights[1].to(device))
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        print(f"   Total parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        
        # Training loop - fewer epochs
        print("\n[4/4] Training LSTM...")
        best_val_f1 = 0
        best_model_state = None
        
        # Reduce epochs from 100 to 30
        for epoch in range(30):
            # Training phase
            self.model.train()
            epoch_loss = 0
            correct = 0
            total = 0
            
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                predicted = (torch.sigmoid(outputs) > 0.5).float()
                correct += (predicted == batch_y).sum().item()
                total += batch_y.size(0)
            
            train_loss = epoch_loss / len(train_loader)
            train_acc = correct / total
            
            # Validation phase
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor.to(device))
                val_loss = criterion(val_outputs, y_val_tensor.to(device)).item()
                val_proba = torch.sigmoid(val_outputs).cpu().numpy().flatten()
                val_pred = (val_proba > 0.5).astype(int)
                val_f1 = f1_score(y_val, val_pred, zero_division=0)
            
            # Store history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_acc'].append(val_f1)
            
            # Save best model by F1 score
            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_model_state = self.model.state_dict().copy()
            
            if (epoch + 1) % 5 == 0:
                print(f"   Epoch {epoch+1}/30 - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, Val F1: {val_f1:.4f}")
        
        # Load best model
        self.model.load_state_dict(best_model_state)
        
        training_time = time.time() - start_time
        
        # Save model
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'input_size': input_size,
            'sequence_length': X_train.shape[1],
            'feature_count': input_size
        }, self.output_dir / 'lstm_model.pth')
        print(f"   ✅ Model saved to: {self.output_dir / 'lstm_model.pth'}")
        
        # Predictions on test set
        self.model.eval()
        with torch.no_grad():
            test_outputs = self.model(X_test_tensor.to(device))
            y_test_proba = torch.sigmoid(test_outputs).cpu().numpy().flatten()
            y_test_pred = (y_test_proba > 0.5).astype(int)
        
        # Metrics
        metrics = {
            'test': self.calculate_metrics(y_test, y_test_pred, y_test_proba),
            'training_time_seconds': round(training_time, 2),
            'model_name': 'LSTM',
            'feature_count': input_size,
            'sequence_length': X_train.shape[1],
            'epochs': 30,
            'batch_size': batch_size
        }
        
        # Save training history
        pd.DataFrame(self.history).to_csv(self.output_dir / 'lstm_training_history.csv', index=False)
        
        # Plot confusion matrix
        self.plot_confusion_matrix(y_test, y_test_pred, "LSTM")
        
        print(f"\n   ✅ Training completed in {training_time:.2f} seconds ({training_time/60:.1f} minutes)")
        print(f"\n   📊 TEST SET METRICS:")
        print(f"      Accuracy:  {metrics['test']['accuracy']:.4f}")
        print(f"      Precision: {metrics['test']['precision']:.4f}")
        print(f"      Recall:    {metrics['test']['recall']:.4f}")
        print(f"      F1-Score:  {metrics['test']['f1_score']:.4f}")
        print(f"      ROC-AUC:   {metrics['test']['roc_auc']:.4f}")
        
        return metrics
    
    def plot_confusion_matrix(self, y_true, y_pred, model_name):
        """Plot confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Greens', 
                    xticklabels=['No Swarm (0)', 'Swarm (1)'],
                    yticklabels=['No Swarm (0)', 'Swarm (1)'])
        plt.title(f'{model_name} - Confusion Matrix', fontsize=14)
        plt.ylabel('Actual Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.tight_layout()
        plt.savefig(self.figures_dir / f'lstm_confusion_matrix.png', dpi=150, bbox_inches='tight')
        plt.close()