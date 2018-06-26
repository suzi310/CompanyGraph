from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['Companies6']

collectionName = 'CompanyShareholdersItem'
set = db[collectionName]


filepath = 'E:/Spider/data/'
filename = filepath + collectionName + '.json'
def main():
    with open(filename, 'w') as f:
        for i in set.find({}):
            for j in i['shareholders_key']:
                record = '{"_from":"CompanyItem' +'/'+ i['company_key'] + '", "_to":"CompanyItem' +'/'+ j +'"},\n'
                f.write(record)
                # print(record)

if __name__ == '__main__':
    main()