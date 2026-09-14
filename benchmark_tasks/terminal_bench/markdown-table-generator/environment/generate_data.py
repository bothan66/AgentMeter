import csv

regions = ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East']
products = ['Widget Pro', 'Widget Lite', 'Gadget Plus', 'Gadget Basic']

# Deterministic sales data
data = [
    ['North America', 'Widget Pro',   145200, 162400, 178900, 191300, 677800],
    ['North America', 'Widget Lite',   87600,  91200,  94500,  99800, 373100],
    ['North America', 'Gadget Plus',  112300, 118700, 125400, 134200, 490600],
    ['North America', 'Gadget Basic',  56400,  58900,  61200,  63700, 240200],
    ['Europe',        'Widget Pro',   131500, 144200, 155600, 162800, 594100],
    ['Europe',        'Widget Lite',   79800,  83400,  87100,  91600, 341900],
    ['Europe',        'Gadget Plus',   98400, 104500, 111200, 118600, 432700],
    ['Europe',        'Gadget Basic',  48200,  50600,  53100,  55800, 207700],
    ['Asia Pacific',  'Widget Pro',   118700, 134500, 151200, 169400, 573800],
    ['Asia Pacific',  'Widget Lite',   72300,  78900,  85600,  93200, 330000],
    ['Asia Pacific',  'Gadget Plus',   89600,  97400, 106200, 115800, 409000],
    ['Asia Pacific',  'Gadget Basic',  43100,  46800,  50900,  55300, 196100],
    ['Latin America', 'Widget Pro',    67400,  73200,  79800,  87100, 307500],
    ['Latin America', 'Widget Lite',   41200,  44600,  48300,  52400, 186500],
    ['Latin America', 'Gadget Plus',   53800,  58200,  63100,  68500, 243600],
    ['Latin America', 'Gadget Basic',  27600,  29800,  32200,  34900, 124500],
    ['Middle East',   'Widget Pro',    54200,  58700,  63800,  69400, 246100],
    ['Middle East',   'Widget Lite',   33100,  35800,  38700,  41900, 149500],
    ['Middle East',   'Gadget Plus',   43200,  46700,  50600,  54900, 195400],
    ['Middle East',   'Gadget Basic',  22100,  23900,  25800,  27900,  99700],
]

with open('/app/data/sales_report.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['region', 'product', 'q1_sales', 'q2_sales', 'q3_sales', 'q4_sales', 'total'])
    writer.writerows(data)

print('CSV created with', len(data), 'rows')
