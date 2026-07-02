from pymongo import MongoClient

uri = "mongodb+srv://vaibhavssingh09_db_user:Clj2TPgnkccB2cx9@cluster0.egji3d0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(uri)

print(client.admin.command("ping"))
