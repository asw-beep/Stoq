import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE, BACKEND_URL } from "@/lib/server";

// Authenticated catch-all proxy: forwards every /api/* request (that isn't a
// dedicated /api/auth/* route) to FastAPI, attaching the JWT from the httpOnly
// cookie as a Bearer token. Server-to-server, so no CORS is needed.
async function handle(request: NextRequest, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;

  const token = (await cookies()).get(AUTH_COOKIE)?.value;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (token) headers.set("authorization", `Bearer ${token}`);

  const init: RequestInit = { method: request.method, headers };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  try {
    const res = await fetch(target, init);
    const body = await res.text();
    return new NextResponse(body || null, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Upstream unavailable" }, { status: 502 });
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
