#!/bin/bash
# Test PriceEdge Suggested Prices Query
# Usage: ./scripts/test_suggested_prices.sh [item_numbers]

ITEM_NUMBERS=${1:-"12345,12346,12347"}

echo "Testing PriceEdge Suggested Prices..."
echo "Item Numbers: $ITEM_NUMBERS"
echo ""

curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d "{
    \"route\": \"/pricing/suggested-prices\",
    \"method\": \"POST\",
    \"body\": {
      \"page\": 1,
      \"nrOfRecords\": 10000,
      \"filters\": [
        {
          \"columnName\": \"cd_ItemNumber\",
          \"op\": \"containsAny\",
          \"value\": \"$ITEM_NUMBERS\"
        }
      ],
      \"fields\": [\"cd_ItemNumber\", \"Value\"],
      \"orderby\": [\"cd_ItemNumber\"]
    }
  }" | jq '.'
