import { NextRequest, NextResponse } from "next/server";

const DATA_API_URL = process.env.DATA_API_URL || "http://api:8000";

async function proxyRequest(
  request: NextRequest,
  path: string[],
  method: string
) {
  const targetPath = path.join("/");

  // Build URL with query parameters
  const queryString = request.nextUrl.searchParams.toString();
  const url = `${DATA_API_URL}/api/v1/${targetPath}${queryString ? `?${queryString}` : ""}`;

  // Forward relevant headers
  const headers: HeadersInit = {};
  const headersToForward = ["authorization", "content-type", "accept", "x-request-id"];
  headersToForward.forEach((key) => {
    const value = request.headers.get(key);
    if (value) headers[key] = value;
  });

  // Default content-type for requests with body
  if (!headers["content-type"] && ["POST", "PUT", "PATCH"].includes(method)) {
    headers["content-type"] = "application/json";
  }

  const fetchOptions: RequestInit = { method, headers };

  // Forward body for methods that support it
  if (["POST", "PUT", "PATCH"].includes(method)) {
    fetchOptions.body = await request.text();
  }

  try {
    const response = await fetch(url, fetchOptions);

    // Check content type before parsing
    const contentType = response.headers.get("content-type");
    const isJson = contentType?.includes("application/json");

    if (isJson) {
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    } else {
      const text = await response.text();
      return new Response(text, {
        status: response.status,
        headers: { "Content-Type": contentType || "text/plain" },
      });
    }
  } catch (error) {
    console.error(`Proxy error for ${method} ${url}:`, error);
    return NextResponse.json(
      { error: "Failed to connect to backend service" },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "GET");
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "POST");
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "PUT");
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "DELETE");
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "PATCH");
}
