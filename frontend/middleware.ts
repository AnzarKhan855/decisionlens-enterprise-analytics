import { NextResponse, type NextRequest } from "next/server";

/**
 * Enterprise Route Protection Middleware
 * - Intercepts requests on Edge/SSR before HTML is generated or dispatched
 * - Blocks unauthenticated access to protected routes, preventing layout shell flashing
 * - Preserves deep links via ?redirect=<destination> query parameter
 * - Automatically redirects authenticated users away from /login and /register
 */

const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-otp",
];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Allow next.js internal assets, static files, and APIs
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".") ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  // Extract session token from cookies
  const token =
    request.cookies.get("decisionlens_token")?.value ||
    request.cookies.get("decisionlens_access_token")?.value ||
    request.cookies.get("token")?.value;

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // If user is unauthenticated and attempting to access a protected page
  if (!token && !isPublicPath) {
    const redirectUrl = new URL("/login", request.url);
    const fullDestination = pathname + (search || "");
    if (fullDestination && fullDestination !== "/") {
      redirectUrl.searchParams.set("redirect", fullDestination);
    }
    return NextResponse.redirect(redirectUrl);
  }

  // If user is already authenticated and visits an auth page (like /login or /register)
  if (token && isPublicPath) {
    const redirectParam = request.nextUrl.searchParams.get("redirect");
    const destination = redirectParam && redirectParam.startsWith("/") ? redirectParam : "/dynamic-dashboard";
    return NextResponse.redirect(new URL(destination, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - static image extensions
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|woff2?|css|js)).*)",
  ],
};
