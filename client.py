import tensorflow as tf
from tensorflow.keras.layers import Dense, Input, Dropout
from tensorflow.keras.models import Sequential
import flwr as fl
import pandas as pd
from sklearn.model_selection import train_test_split
import argparse
import traceback
import numpy as np # Added this import
from sklearn.preprocessing import StandardScaler
import joblib # Import joblib
import os # Import os for directory creation

def main():
    parser = argparse.ArgumentParser(description="Flower client for a specific store.")
    parser.add_argument("--store", type=str, required=True, choices=['A', 'B', 'C'], help="Store identifier (A, B, or C)")
    args = parser.parse_args()

    # Create a log file for the client
    log_file = f"simulation_logs/client_{args.store.lower()}_log.txt"
    with open(log_file, "w") as f:
        f.write(f"Client {args.store} Log\n")
        f.write("="*20 + "\n")

    # Create a directory for scalers if it doesn't exist
    scalers_dir = "scalers"
    if not os.path.exists(scalers_dir):
        os.makedirs(scalers_dir)

    try:
        # Load the data
        df = pd.read_csv(f'Store_{args.store}_dataset.csv')

        # Clean and preprocess the data
        df.drop('Unnamed: 0', axis=1,inplace=True)
        # df = pd.get_dummies(data, columns=["Gender","Promotion_Type", "Channel", "Time_of_Day"], drop_first=True)
        # Rename the specific column
        #if 'Channel_In-store' in df.columns:
        #df.rename(columns={'Channel_In-store': 'Channel_In_store'}, inplace=True)
        #bool_features = df.select_dtypes(include=bool).columns
        #df[bool_features]=df[bool_features].astype(int)

        X=df.drop('Will_Buy', axis = 1)
        y=df['Will_Buy']

        x_train, x_test, y_train, y_test = train_test_split(X,y, test_size=0.2, random_state = 42)
        
        sc=StandardScaler()
        x_train=sc.fit_transform(x_train)
        x_test = sc.transform(x_test)

        # Save the fitted scaler
        scaler_filename = os.path.join(scalers_dir, f"scaler_store_{args.store.lower()}.joblib")
        joblib.dump(sc, scaler_filename)
        with open(log_file, "a") as f:
            f.write(f"Saved StandardScaler to {scaler_filename}\n")

        # Handle class imbalance with SMOTE
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        x_train, y_train = smote.fit_resample(x_train, y_train)
        

        # Check for class imbalance or missing classes in y_train
        unique_classes = np.unique(y_train)
        if len(unique_classes) < 2:
            with open(log_file, "a") as f:
                f.write(f"\n--- WARNING ---\n")
                f.write(f"Client {args.store}: Training data (y_train) contains less than 2 unique classes ({unique_classes}). "
                        "Cannot train Keras model. Client will not connect to the server.\n")
            return # Exit the main function here

        # Create a Keras model
        model = Sequential()
        input_dim = x_train.shape[1]
        model.add(Input(shape=(input_dim,)))
        model.add(Dense(64, activation='relu')) # Hidden layer 1
        model.add(Dropout(0.3)) # Dropout for regularization
        model.add(Dense(32, activation='relu')) # Hidden layer 2
        model.add(Dropout(0.3))
        model.add(Dense(1, activation='sigmoid')) # Output layer
        #model.add(Dense(1,activation='sigmoid', kernel_initializer='zeros', bias_initializer='zeros'))

        model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=0.01),
                        loss="binary_crossentropy",
                        metrics=["accuracy"])

        class FlowerClient(fl.client.NumPyClient):

            def get_parameters(self, config):
                return model.get_weights()

            def fit(self, parameters, config):
                model.set_weights(parameters)
                history = model.fit(x_train, y_train,class_weight={0:2, 1:1}, epochs = 10, batch_size=32, validation_split=0.1, verbose=0)
                
                # Log training metrics
                loss = history.history['loss'][0]
                acc = history.history['accuracy'][0]
                val_acc = history.history['val_accuracy'][0]
                with open(log_file, "a") as f:
                    f.write(f"Round {config.get('server_round', 'N/A')}: Fit - Loss: {loss}, Accuracy: {acc}, Val Accuracy: {val_acc}\n")
                    
                return model.get_weights(),len(x_train),{"accuracy": acc}
            
            def evaluate(self, parameters, config):
                model.set_weights(parameters)
                loss,accuracy = model.evaluate(x_test, y_test, verbose=0)
                
                # Log evaluation metrics
                with open(log_file, "a") as f:
                    f.write(f"Round {config.get('server_round', 'N/A')}: Evaluate - Loss: {loss}, Accuracy: {accuracy}\n")
                    
                return loss, len(x_test), {"accuracy": accuracy}
            
        # Start the client ONLY IF data checks pass
        fl.client.start_client(server_address="127.0.0.1:8080", client=FlowerClient().to_client())

    except Exception as e:
        with open(log_file, "a") as f:
            f.write("\n--- ERROR ---\n")
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()