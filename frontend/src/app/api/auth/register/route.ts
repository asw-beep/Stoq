import { NextResponse } from "next/server";

import { BACKEND_URL } from "@/lib/server";

// Forwards registration to the backend. The user then logs in explicitly.
export async function POST(request: Request) {
  const body = await request.text();
  const res = await fetch(`${BACKEND_URL}/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
