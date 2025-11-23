import { redirect, type MiddlewareFunction } from "react-router";
import { authenticate, setUserContext } from "./common";

/**
 * Admin authentication middleware for admin pages
 * Supports two authentication methods:
 * 1. Header authentication (priority) - use ADMIN_AUTH_HEADER and ADMIN_AUTH_SECRET
 * 2. Session authentication (fallback) - use session in Cookie
 * 
 * Redirect to /unauthorized page if authentication fails
 */
export const adminAuthMiddleware: MiddlewareFunction = async ({
  request,
  context,
}) => {
  // Execute common authentication logic
  const authResult = await authenticate(request, context);

  if (!authResult.success) {
    // Authentication failed, redirect to unauthorized page
    throw redirect("/unauthorized");
  }

  // Validate if user is admin (Header authentication is automatically admin, session authentication needs to be checked)
  if (authResult.user.role !== "admin") {
    // Non-admin user, redirect to unauthorized page
    throw redirect("/unauthorized");
  }

  // Authentication successful, set user context
  setUserContext(context, authResult.user);
};
