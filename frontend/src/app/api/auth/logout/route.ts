import { NextResponse } from "next/server";

import { AUTH_COOKIE } from "@/lib/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(AUTH_COOKIE);
  return response;
}
