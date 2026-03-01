from graphviz import Digraph

dot = Digraph(format="png")
dot.attr(rankdir="TB", size="8,10")

# Layers
dot.node("Users", "Users / Applications")
dot.node("API", "API Gateway / Application Layer")
dot.node("Inference", "Real-Time Inference Service")
dot.node("FeatureStore", "Feature Store\n(Online + Offline)")
dot.node("Registry", "Model Registry")
dot.node("Training", "Training Pipeline\n- Preprocessing\n- Feature Eng\n- Training\n- Evaluation")
dot.node("DataLake", "Data Lake / Warehouse")
dot.node("Monitoring", "Monitoring & Logging")

# Connections
dot.edge("Users", "API")
dot.edge("API", "Inference")
dot.edge("Inference", "FeatureStore")
dot.edge("FeatureStore", "Inference")
dot.edge("Training", "Registry")
dot.edge("Registry", "Inference")
dot.edge("DataLake", "Training")
dot.edge("Inference", "Monitoring")
dot.edge("Monitoring", "DataLake")

# Save
dot.render("ai_architecture", cleanup=True)

print("Saved as ai_architecture.png")