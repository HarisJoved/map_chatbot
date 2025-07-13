# Fiware Integration with Graphiti

This document describes the Fiware sensor data integration with Graphiti for storing sensor data in Neo4j and creating vector embeddings.

## Overview

The Fiware integration allows you to:
1. Receive real-time sensor data from Fiware via webhooks
2. Store sensor data in Neo4j database
3. Create semantic embeddings using Graphiti
4. Search sensor data using natural language queries
5. Get statistics about stored sensor data

## Architecture

```
Fiware Sensor → Webhook → FastAPI → Neo4j + Graphiti → Vector Database
```

### Components

- **FiwareDataProcessor**: Main processor that handles sensor data
- **Graphiti Integration**: Creates embeddings and enables semantic search
- **Neo4j Storage**: Stores structured sensor data
- **FastAPI Endpoints**: REST API for webhook and search operations

## API Endpoints

### 1. Fiware Webhook (`POST /api/fiware/webhook`)

Receives Fiware sensor data and processes it.

**Request Body:**
```json
{
  "subscriptionId": "68396afe2ee3240a510d7b32",
  "data": [
    {
      "id": "urn:ngsi-v2:SolarEnergy:001",
      "type": "SolarEnergy",
      "location": {
        "type": "geo:json",
        "value": {
          "type": "Point",
          "coordinates": [144.9583, -37.8033]
        },
        "metadata": {
          "TimeInstant": {
            "type": "DateTime",
            "value": "2025-05-30T08:53:11.686Z"
          }
        }
      },
      "Voltage": {
        "type": "float",
        "value": 220.1,
        "metadata": {
          "TimeInstant": {
            "type": "DateTime",
            "value": "2025-05-30T08:53:11.686Z"
          }
        }
      },
      "current": {
        "type": "Text",
        "value": 89.8,
        "metadata": {
          "TimeInstant": {
            "type": "DateTime",
            "value": "2025-05-30T08:53:11.686Z"
          }
        }
      },
      "TimeInstant": {
        "type": "DateTime",
        "value": "2025-05-30T08:53:11.686Z",
        "metadata": {}
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Processed 1 sensor readings",
  "processed_sensors": 1,
  "sensor_ids": ["urn:ngsi-v2:SolarEnergy:001"],
  "errors": []
}
```

### 2. Sensor Search (`POST /api/fiware/search`)

Search sensor data using semantic search via Graphiti.

**Request Body:**
```json
{
  "query": "solar energy sensors with high voltage",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "sensor_id": "urn:ngsi-v2:SolarEnergy:001",
      "sensor_type": "SolarEnergy",
      "timestamp": "2025-05-30T08:53:11.686Z",
      "longitude": 144.9583,
      "latitude": -37.8033,
      "relevance_score": 0.85,
      "text": "Sensor Data Report: - Sensor ID: urn:ngsi-v2:SolarEnergy:001..."
    }
  ],
  "total_count": 1
}
```

### 3. Sensor Statistics (`GET /api/fiware/statistics`)

Get statistics about stored sensor data.

**Response:**
```json
{
  "total_sensors": 150,
  "sensor_types": 5,
  "earliest_reading": "2025-01-01T00:00:00Z",
  "latest_reading": "2025-05-30T08:53:11.686Z"
}
```

### 4. Health Check (`GET /api/fiware/health`)

Check the health of the Fiware integration.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "graphiti_initialized": true,
  "total_sensors": 150,
  "sensor_types": 5
}
```

## Data Flow

### 1. Webhook Reception
- Fiware sends sensor data to `/api/fiware/webhook`
- Data is validated using Pydantic models
- Each sensor reading is processed individually

### 2. Neo4j Storage
- Sensor data is stored in Neo4j with the following structure:
  - Node: `Sensor` with properties: `id`, `type`, `longitude`, `latitude`, `timestamp`, `attributes`
  - Attributes are stored as JSON string

### 3. Graphiti Embedding
- Sensor data is converted to descriptive text
- Text is embedded using Google Gemini embeddings
- Embeddings are stored in Graphiti's vector database
- Metadata includes sensor ID, type, location, and timestamp

### 4. Semantic Search
- User queries are embedded using the same model
- Graphiti performs similarity search
- Results are ranked by relevance score
- Metadata is returned with search results

## Configuration

### Environment Variables

```bash
# Neo4j Configuration
NEO4J_URI=neo4j+ssc://your-neo4j-instance
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Google Gemini Configuration
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.0-flash

# Pinecone Configuration (for vector storage)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east1-aws
PINECONE_INDEX=locations-index
PINECONE_DIM=768
```

### Graphiti Configuration

The system uses Google Gemini for:
- **LLM**: `gemini-2.0-flash` for text generation
- **Embeddings**: `embedding-001` for creating vector embeddings
- **Reranking**: `gemini-2.5-flash-lite-preview-06-17` for result ranking

## Testing

Run the test script to verify the integration:

```bash
cd backend
python test_fiware.py
```

This will test:
1. Health check endpoint
2. Webhook data processing
3. Sensor search functionality
4. Statistics endpoint

## Usage Examples

### 1. Setting up Fiware Webhook

Configure your Fiware instance to send webhooks to:
```
http://your-server:8000/api/fiware/webhook
```

### 2. Searching Sensor Data

```python
import requests

# Search for high voltage sensors
response = requests.post(
    "http://localhost:8000/api/fiware/search",
    json={
        "query": "sensors with voltage above 200V",
        "limit": 10
    }
)

results = response.json()
for result in results["results"]:
    print(f"Sensor: {result['sensor_id']}")
    print(f"Type: {result['sensor_type']}")
    print(f"Score: {result['relevance_score']}")
    print("---")
```

### 3. Getting Statistics

```python
import requests

response = requests.get("http://localhost:8000/api/fiware/statistics")
stats = response.json()

print(f"Total sensors: {stats['total_sensors']}")
print(f"Sensor types: {stats['sensor_types']}")
print(f"Latest reading: {stats['latest_reading']}")
```

## Error Handling

The system includes comprehensive error handling:

1. **Webhook Validation**: Invalid data is rejected with detailed error messages
2. **Neo4j Errors**: Database connection issues are logged and reported
3. **Graphiti Errors**: Embedding failures are handled gracefully
4. **API Errors**: All endpoints return appropriate HTTP status codes

## Monitoring

Monitor the system using:

1. **Health Check**: Regular health checks to ensure system availability
2. **Statistics**: Track sensor data volume and types
3. **Logs**: Comprehensive logging for debugging and monitoring
4. **Error Tracking**: Failed operations are logged with details

## Performance Considerations

1. **Batch Processing**: Multiple sensors in a single webhook are processed efficiently
2. **Async Operations**: Non-blocking processing for better performance
3. **Connection Pooling**: Neo4j connections are reused
4. **Caching**: Consider implementing caching for frequently accessed data

## Security

1. **Input Validation**: All webhook data is validated using Pydantic
2. **Error Sanitization**: Error messages don't expose sensitive information
3. **Rate Limiting**: Consider implementing rate limiting for production use
4. **Authentication**: Add authentication for production deployments

## Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   - Check Neo4j URI, username, and password
   - Verify Neo4j instance is running
   - Check network connectivity

2. **Graphiti Initialization Failed**
   - Verify Google API key is valid
   - Check API quotas and limits
   - Ensure required models are available

3. **Webhook Processing Errors**
   - Validate webhook data format
   - Check sensor data structure
   - Review error logs for details

### Debug Mode

Enable debug logging by setting:
```bash
DEBUG=True
```

This will provide detailed logs for troubleshooting.

## Future Enhancements

1. **Real-time Updates**: WebSocket support for real-time sensor data
2. **Advanced Analytics**: Time-series analysis and trend detection
3. **Alert System**: Configurable alerts based on sensor thresholds
4. **Data Export**: Export functionality for sensor data
5. **Multi-tenant Support**: Support for multiple organizations
6. **Advanced Search**: Filtering by time range, location, sensor type 