import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8080";
const INTERNAL_KEY = process.env.INTERNAL_API_KEY || "";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const url = `${API_BASE}/api/public/${path}${search}`;

  try {
    const res = await fetch(url, {
      headers: { "X-Internal-Key": INTERNAL_KEY },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { detail: "API no disponible" },
      { status: 502 }
    );
  }
}
