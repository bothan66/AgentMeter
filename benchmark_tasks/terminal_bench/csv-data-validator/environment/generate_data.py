import csv

rows = [
    # id, name, email, department, salary, hire_date, manager_id
    [1,  'Alice Johnson',   'alice@example.com',       'Engineering',  95000,  '2020-03-15', ''],
    [2,  'Bob Smith',       'bob@company.org',          'Marketing',    72000,  '2019-07-01', '1'],
    [3,  'Carol Davis',     'carol@tech.io',            'Engineering',  88000,  '2021-01-10', '1'],
    [4,  'David Lee',       'david@example.com',        'HR',           60000,  '2018-11-20', ''],
    [5,  'Eve Martinez',    'evemartinezNOATSIGN',      'Finance',      75000,  '2020-05-05', '4'],  # Error1: invalid email
    [6,  'Frank Wilson',    'frank@company.com',        'Engineering',  105000, '2017-08-30', '1'],
    [7,  'Grace Brown',     'grace@startup.co',         'Product',      92000,  '2022-02-14', '1'],
    [8,  'Henry Taylor',    'henry@example.com',        'Engineering',  78000,  '2019-03-22', '6'],
    [2,  'Ivan Clark',      'ivan@example.com',         'Marketing',    68000,  '2021-09-09', '2'],  # Error2: duplicate id=2
    [10, 'Julia White',     'julia@corp.net',           'Finance',      83000,  '2020-12-01', '4'],
    [11, 'Kevin Harris',    'kevin@example.com',        'HR',           57000,  '2016-06-18', '4'],
    [12, 'Laura Thomas',    'laura@tech.com',           'Engineering',  99000,  '2018-04-25', '1'],
    [13, 'Mike Jackson',    'mike@company.io',          'Product',      87000,  '2021-07-07', '7'],
    [14, 'Nancy White',     'nancy@example.com',        'Sales',        500,    '2020-10-10', ''],   # Error3: salary too low
    [15, 'Oscar Robinson',  'oscar@biz.com',            'Engineering',  110000, '2015-01-30', '1'],
    [16, 'Paula Lewis',     'paula@example.com',        'Marketing',    65000,  '2023-03-03', '2'],
    [17, 'Quinn Walker',    'quinn@startup.io',         'Finance',      79000,  '2019-05-12', '4'],
    [18, 'Rachel Hall',     'rachel@corp.com',          'HR',           600000, '2020-08-08', '4'],  # Error4: salary too high
    [19, 'Sam Allen',       'sam@example.com',          'Engineering',  95500,  '2022-11-11', '6'],
    [20, 'Tina Young',      'tina@company.net',         'Product',      83000,  '2021-04-04', '7'],
    [21, 'Ursula Hernandez','ursula@tech.org',          'Sales',        72000,  '2018-09-15', ''],
    [22, 'Victor King',     'victor@biz.io',            'Engineering',  88500,  '2020-01-20', '1'],
    [23, 'Wendy Wright',    'wendy@example.com',        'Finance',      91000,  '2025-06-01', '4'],  # Error5: future hire_date
    [24, 'Xavier Scott',    'xavier@corp.com',          'Marketing',    67000,  '2017-12-12', '2'],
    [25, 'Yvonne Green',    'yvonne@startup.net',       'HR',           55000,  '2023-07-07', '4'],
    [26, 'Zach Baker',      'zach@example.com',         'Engineering',  102000, '2016-03-28', '1'],
    [27, 'Amy Carter',      'amy@company.com',          'Product',      86000,  '2021-10-10', '7'],
    [28, 'Brian Mitchell',  'brian@tech.io',            'Sales',        74000,  '2019-02-14', '21'],
    [29, 'Cynthia Perez',   'cynthia@biz.com',          'Engineering',  93000,  '2020-06-30', '6'],
    [30, 'Daniel Roberts',  'daniel@corp.net',          'Finance',      80000,  '2022-08-25', '4'],
    [31, 'Elena Turner',    'elena@example.com',        'HR',           58000,  '31-12-2019', '4'],  # Error6: wrong date format
    [32, 'Finn Phillips',   'finn@company.org',         'Engineering',  96000,  '2018-07-17', '1'],
    [33, 'Gina Campbell',   'gina@startup.io',          'Marketing',    70000,  '2021-01-25', '2'],
    [34, 'Hank Parker',     'hank@tech.com',            'Product',      85000,  '2020-04-16', '7'],
    [35, 'Iris Evans',      'iris@biz.org',             'Sales',        76000,  '2017-10-03', '21'],
    [36, 'Jack Edwards',    'jack@example.com',         'Engineering',  89000,  '2019-11-08', '6'],
    [37, 'Karen Collins',   'karencollins@nodotdomain', 'Finance',      82000,  '2022-03-19', '4'],  # Error7: email no dot after @
    [38, 'Liam Stewart',    'liam@corp.com',            'HR',           56000,  '2023-09-01', '4'],
    [39, 'Mia Sanchez',     'mia@company.net',          'Engineering',  97000,  '2015-05-20', '1'],
    [40, 'Noah Morris',     'noah@startup.com',         'Product',      84000,  '2021-12-12', '7'],
    [41, 'Olivia Rogers',   'olivia@tech.io',           'Sales',        73000,  '2018-08-08', '21'],
    [42, 'Peter Reed',      'peter@biz.com',            'Marketing',    69000,  '2020-02-28', '2'],
    [43, 'Quinn Cook',      'quinn2@example.com',       'Engineering',  100000, '2016-11-15', '1'],
    [44, 'Rosa Bell',       'rosa@corp.org',            'Finance',      78000,  '2019-04-04', '9999'], # Error8: manager_id 9999 not exist
    [45, 'Steve Murphy',    'steve@company.io',         'HR',           59000,  '2022-05-05', '4'],
    [46, 'Tara Bailey',     'tara@startup.net',         'Engineering',  94000,  '2017-07-22', '1'],
    [47, 'Uma Rivera',      'uma@tech.com',             'Product',      87500,  '2021-03-03', '7'],
    [48, 'Vince Cooper',    'vince@biz.io',             'Sales',        75500,  '2020-09-09', '21'],
    [49, 'Wilma Richardson','wilma@example.com',        'Marketing',    66000,  '2023-01-15', '2'],
    [50, 'Xena Cox',        'xena@corp.com',            'Engineering',  98000,  '2018-10-10', '1'],
]

with open('/app/data/employees.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['employee_id', 'name', 'email', 'department', 'salary', 'hire_date', 'manager_id'])
    writer.writerows(rows)

print(f'Created employees.csv with {len(rows)} rows')
