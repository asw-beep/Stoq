import { NextResponse } from "next/server";

import { AUTH_COOKIE, BACKEND_URL } from "@/lib/server";

// Exchanges credentials for a JWT and stores it in an httpOnly cookie. The token
// is never returned to the browser (XSS-safe) — only the user object is.
export async function POST(request: Request) {
  const { email, password } = await request.json();

  const form = new URLSearchParams({ username: email, password });
  const res = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    return NextResponse.json(
      { detail: "Incorrect email or password" },
      { status: res.status === 429 ? 429 : 401 },
    );
  }

  const { access_token } = await res.json();

  const meRes = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { authorization: `Bearer ${access_token}` },
  });
  const user = meRes.ok ? await meRes.json() : null;

  const response = NextResponse.json({ user });
  response.cookies.set({
    name: AUTH_COOKIE,
    value: access_token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
  });
  return response;
}
