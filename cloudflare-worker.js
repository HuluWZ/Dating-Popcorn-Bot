/**
 * Cloudflare Worker for serving S3 images
 * 
 * This worker proxies requests to S3, keeping the bucket name private
 * and providing free CDN benefits (50k requests/day free).
 * 
 * Setup:
 * 1. Deploy this worker to Cloudflare Workers
 * 2. Set the following environment variables (secrets) in Cloudflare:
 *    - AWS_ACCESS_KEY_ID
 *    - AWS_SECRET_ACCESS_KEY
 *    - S3_BUCKET_NAME
 *    - AWS_REGION (default: us-east-1)
 *    - AWS_ENDPOINT_URL_S3 (only for non-AWS storage such as Neon)
 * 3. Update your .env file with the worker URL
 * 
 * Usage:
 * - Worker URL: https://your-worker-name.your-subdomain.workers.dev
 * - Image URL format: https://your-worker-name.your-subdomain.workers.dev/reviews/uuid.jpg
 */

export default {
  async fetch(request, env) {
    // Only allow GET requests
    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Get the path from the URL (e.g., /reviews/uuid.jpg)
    const url = new URL(request.url);
    let s3Key = url.pathname;
    
    // Remove leading slash if present
    if (s3Key.startsWith('/')) {
      s3Key = s3Key.slice(1);
    }
    
    // Remove trailing slash if present
    if (s3Key.endsWith('/')) {
      s3Key = s3Key.slice(0, -1);
    }

    // Validate that we have a path
    if (!s3Key || s3Key.trim() === '') {
      return new Response('Bad Request: Missing image path', { 
        status: 400,
        headers: {
          'Content-Type': 'text/plain'
        }
      });
    }

    // Get AWS credentials from environment variables
    const awsAccessKeyId = env.AWS_ACCESS_KEY_ID;
    const awsSecretAccessKey = env.AWS_SECRET_ACCESS_KEY;
    const bucketName = env.S3_BUCKET_NAME;
    const region = env.AWS_REGION || 'us-east-1';

    if (!awsAccessKeyId || !awsSecretAccessKey || !bucketName) {
      return new Response('Server Error: AWS credentials not configured', { status: 500 });
    }

    try {
      // Generate signed request for S3
      const signedRequest = await generateSignedRequest(
        bucketName,
        s3Key,
        region,
        awsAccessKeyId,
        awsSecretAccessKey,
        env.AWS_ENDPOINT_URL_S3
      );

      // Fetch the image from S3 with signed headers
      const imageResponse = await fetch(signedRequest.url, {
        method: 'GET',
        headers: signedRequest.headers,
      });

      // If S3 returns an error, provide detailed error message
      if (!imageResponse.ok) {
        const status = imageResponse.status;
        const statusText = imageResponse.statusText;
        let errorMessage = `Image not found (${status} ${statusText})`;
        
        // Try to get error details from S3 response
        try {
          const errorText = await imageResponse.text();
          
          // Provide more specific error messages
          if (status === 403) {
            errorMessage = 'Access denied. Check AWS credentials and S3 permissions.';
          } else if (status === 404) {
            errorMessage = 'Image not found in S3.';
          } else if (status === 400) {
            errorMessage = `Bad request from S3: ${errorText.substring(0, 200)}`;
          }
          
          // Log detailed error for debugging
          console.error('S3 Error:', {
            status,
            s3Key,
            bucket: bucketName,
            error: errorText.substring(0, 200)
          });
        } catch (e) {
          console.error('Error reading S3 error response:', e);
        }
        
        return new Response(errorMessage, { 
          status: status,
          headers: {
            'Content-Type': 'text/plain',
          }
        });
      }

      // Get the image data
      const imageData = await imageResponse.arrayBuffer();
      
      // Determine content type from file extension
      const contentType = getContentType(s3Key);

      // Return the image with appropriate headers
      return new Response(imageData, {
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'public, max-age=31536000', // Cache for 1 year
          'Access-Control-Allow-Origin': '*', // Allow CORS if needed
        },
      });
    } catch (error) {
      console.error('Error fetching from S3:', error);
      return new Response('Internal Server Error', { status: 500 });
    }
  },
};

/**
 * Generate a signed request for S3 object access using AWS Signature Version 4
 */
async function generateSignedRequest(bucket, key, region, accessKeyId, secretAccessKey, endpoint) {
  // Validate inputs
  if (!bucket || !key || !region || !accessKeyId || !secretAccessKey) {
    throw new Error('Missing required parameters for S3 signing');
  }
  
  // URL encode the key for the canonical URI
  // S3 expects each path segment to be encoded, but slashes should remain as-is
  // For example: "reviews/image.jpg" -> "/reviews/image.jpg" (no encoding needed for simple paths)
  // But if there are special chars: "reviews/my image.jpg" -> "/reviews/my%20image.jpg"
  
  // Split by slash, encode each segment, then rejoin
  const pathSegments = key.split('/');
  const encodedSegments = pathSegments.map(segment => encodeURIComponent(segment));
  const encodedKey = encodedSegments.join('/');
  // Custom S3-compatible endpoint (e.g. Neon storage) uses path-style: /bucket/key
  const canonicalUri = endpoint ? `/${bucket}/${encodedKey}` : `/${encodedKey}`;
  
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:\-]|\.\d{3}/g, '');
  const dateStamp = amzDate.substr(0, 8);
  
  // Build the host header (handle different S3 endpoint formats)
  const host = endpoint ? new URL(endpoint).host : `${bucket}.s3.${region}.amazonaws.com`;
  
  // Create canonical request
  // For GET requests, we use UNSIGNED-PAYLOAD and include x-amz-content-sha256 header
  const canonicalQueryString = '';
  const payloadHash = 'UNSIGNED-PAYLOAD';
  const canonicalHeaders = `host:${host}\nx-amz-content-sha256:${payloadHash}\nx-amz-date:${amzDate}\n`;
  const signedHeaders = 'host;x-amz-content-sha256;x-amz-date';
  
  const canonicalRequest = `GET\n${canonicalUri}\n${canonicalQueryString}\n${canonicalHeaders}\n${signedHeaders}\n${payloadHash}`;
  
  // Create string to sign
  const algorithm = 'AWS4-HMAC-SHA256';
  const credentialScope = `${dateStamp}/${region}/s3/aws4_request`;
  const canonicalRequestHash = await sha256(canonicalRequest);
  const stringToSign = `${algorithm}\n${amzDate}\n${credentialScope}\n${toHex(canonicalRequestHash)}`;
  
  // Calculate signature
  const kDate = await hmacSha256(`AWS4${secretAccessKey}`, dateStamp);
  const kRegion = await hmacSha256(kDate, region);
  const kService = await hmacSha256(kRegion, 's3');
  const kSigning = await hmacSha256(kService, 'aws4_request');
  const signature = await hmacSha256(kSigning, stringToSign);
  
  // Create authorization header
  const authorization = `${algorithm} Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${toHex(signature)}`;
  
  // Build S3 URL (use encoded key in URL)
  const s3Url = `https://${host}${canonicalUri}`;
  
  return {
    url: s3Url,
    headers: {
      'Authorization': authorization,
      'x-amz-date': amzDate,
      'x-amz-content-sha256': payloadHash,
      'Host': host
    },
  };
}

/**
 * Helper function to get content type from file extension
 */
function getContentType(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const contentTypes = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
  };
  return contentTypes[ext] || 'application/octet-stream';
}

/**
 * SHA-256 hash function
 */
async function sha256(message) {
  const msgBuffer = typeof message === 'string' ? new TextEncoder().encode(message) : message;
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  return new Uint8Array(hashBuffer);
}

/**
 * HMAC-SHA256 function
 */
async function hmacSha256(key, message) {
  const keyBuffer = typeof key === 'string' ? new TextEncoder().encode(key) : key;
  const msgBuffer = typeof message === 'string' ? new TextEncoder().encode(message) : message;
  
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBuffer,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  const signature = await crypto.subtle.sign('HMAC', cryptoKey, msgBuffer);
  return new Uint8Array(signature);
}

/**
 * Convert Uint8Array to hex string
 */
function toHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

