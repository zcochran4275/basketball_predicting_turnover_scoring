## 🏀 Graph Neural Networks — Turnover-to-Score Prediction in Basketball

We explore **Graph Neural Networks (GNNs)** to predict the probability that a **turnover** leads to an opponent scoring opportunity.

We use **NBA tracking data** from  
👉 [Hugging Face: dcayton/nba_tracking_data_15_16](https://huggingface.co/datasets/dcayton/nba_tracking_data_15_16)

Steps include:
1. Detecting turnover events and defining possessions  
2. Encoding **player–team–ball** relationships as graph structures  
3. Defining:
   - **Node features:** position (x, y), speed, direction, turnover flag  
   - **Edge features:** coordinate distance, speed difference  
4. Labeling turnovers that lead to opponent scores within the next 10 seconds  
5. Training and visualizing a **GNN classifier** to predict these outcomes  
