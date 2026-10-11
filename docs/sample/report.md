# Data Quality Report

- **Source:** orders_dirty.csv
- **Rules:** orders
- **Status:** FAIL
- **Rows checked:** 202
- **Rows with errors:** 10 (row pass rate 95.0%)
- **Errors:** 11, **Warnings:** 1

## Issues by rule

| Rule | Count |
| --- | --- |
| allowed | 2 |
| type | 2 |
| unique | 2 |
| column_count | 1 |
| duplicate_row | 1 |
| max | 1 |
| min | 1 |
| pattern | 1 |
| required | 1 |

## Issues by column

| Column | Count |
| --- | --- |
| amount | 3 |
| (dataset) | 2 |
| customer_email | 2 |
| order_id | 2 |
| order_date | 1 |
| region | 1 |
| status | 1 |

## Examples

### allowed
- line 43, status: 'shiped' is not one of ['pending', 'shipped', 'delivered', 'cancelled'] (error)
- line 52, region: 'Mars' is not one of ['Midwest', 'Northeast', 'South', 'West'] (warning)

### column_count
- line 203: row has 2 fields, expected 6 (error)

### duplicate_row
- line 202: row is identical to line 82 (error)

### max
- line 32, amount: 99999 is above the maximum of 10000 (error)

### min
- line 24, amount: -12.50 is below the minimum of 0 (error)

### pattern
- line 12, customer_email: 'not-an-email' does not match the required pattern (error)

### required
- line 5, customer_email: value is missing (error)

### type
- line 17, order_date: '2026-13-45' is not a valid date (error)
- line 72, amount: 'abc' is not a valid float (error)

### unique
- line 62, order_id: '1059' already appears on line 61 (error)
- line 202, order_id: '1080' already appears on line 82 (error)
