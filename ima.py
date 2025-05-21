import csv

entries = [
    {"first_name":"chetan","last_name":"Kumar"},
    {"first_name":"chetan1","last_name":"Kumar1"},
    {"first_name":"chetan2","last_name":"Kumar2"},
    {"first_name":"chetan3","last_name":"Kumar3"},
    {"first_name":"chetan4","last_name":"Kumar4"},
    {"first_name":"chetan5","last_name":"Kumar5"},
    {"first_name":"chetan6","last_name":"Kumar6"},
    {"first_name":"chetan7","last_name":"Kumar7"}
]

with open('ne2w.csv',mode="r") as csvfile:
    fieldNames = entries[0].keys()
    writer = csv.DictWriter(csvfile,fieldNames)
    writer.writeheader()
    for i in range(0,20000000):
        writer.writerows(entries)
        