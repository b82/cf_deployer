use admin
db.createUser(
  {
    user: "deployer",
    pwd: "deployer",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
  }
)
use deployer-demo
db.createCollection('deployerCollection')
db.deployerCollection.insertMany([
  {"name":"Bile","dept":"BPO","Salary":50000},
  {"name":"Ferro","dept":"IT","Salary":90000},
  {"name":"Franz","dept":"IT","Salary":50000},
  {"name":"Manuel","dept":"IT","Salary":50000}
])