import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE } from "@/lib/server";

// Next.js 16 renamed Middleware -> Proxy (same functionality). This is an
// optimistic cookie-presence guard, not the authorization boundary — the
// backend re-validates the JWT on every /api call.
const PUBLIC_PATHS = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasToken = Boolean(request.cookies.get(AUTH_COOKIE)?.value);
  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );

  if (!hasToken && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (hasToken && isPublic) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Run on app pages only — exclude /api (BFF), Next internals, and static files.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
