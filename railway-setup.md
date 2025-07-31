# Railway Deployment Setup Guide

## Environment Variables Required

You need to set the following environment variables in your Railway project:

### Required Variables:
1. **PINECONE_API_KEY** - Your Pinecone API key
2. **OPENAI_API_KEY** - Your OpenAI API key
3. **PINECONE_INDEX_NAME** - Your Pinecone index name
4. **PINECONE_HOST** - Your Pinecone index host URL

### Optional Variables:
- **SECRET_KEY** - A secure secret key for JWT tokens (defaults to a development key)
- **ENVIRONMENT** - Set to "production" for production deployment
- **DEBUG** - Set to "false" for production

## How to Set Environment Variables in Railway:

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the "Variables" tab
4. Add each environment variable with its corresponding value

## Example Environment Variables:
```
PINECONE_API_KEY=your-pinecone-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
PINECONE_INDEX_NAME=your-index-name
PINECONE_HOST=https://your-index-name-your-project.svc.pinecone.io
SECRET_KEY=your-secure-secret-key-here
ENVIRONMENT=production
DEBUG=false
```

## Health Check Endpoint

After deployment, you can check the health of your service at:
`https://your-railway-app.railway.app/health`

This will show you the status of all services including Pinecone and OpenAI connections.

## Troubleshooting

If you see "degraded" status in the health check, it means one or more services are not properly configured. Check the error messages in the health response to identify which environment variables are missing or incorrect. 