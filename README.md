# foursquare_explorer
This script queries the number of recommended venues in a specified grid arount a start location.
## How it works
1. Takes an area of HEIGHT by WIDTH kilometers centered on START point.
2. Divides this area into smaller squares with specified STEP.
3. Uses the Foursquare API to get a [list of venue categories](https://developer.foursquare.com/docs/api/venues/categories).
4. Queries the [Foursquare Explore API](https://developer.foursquare.com/docs/api/venues/explore) with the following parameters:
   * Center of each square as location
   * Specified RADIUS
   * First query is sent without categoryId, then a request is sent for each category ID except for IGNORED_CATEGORIES.
5. Output geojson is saved as GEOJSON_FILE where every square is stored as a Polygon named Square N.
6. Venue data is saved as CSV to DATA_FILE.  
### Foursquare API Limitations
Foursquare API limits the number of calls to venues/* endpoints for free verified accounts to 5000 per hour. The current remaining limit is returned in X-RateLimit-Remaining header and the timestamp when the limit will be reset is passed in X-RateLimit-Reset header. If the remaining limit falls below 10 the script will pause until the reset time.
### Foursquare credentials
You will need to create a secrets.json file in the same directory as the script. The file should contain your client ID, secret and API version
```json
{
  "CLIENT_ID": "your_client_id",
  "CLIENT_SECRET": "your_client_secret",
  "VERSION": "20190425"
}
```

