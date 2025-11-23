import { UserContext, EnvContext } from "~/context";
import {
  getSessionFromRequest,
  validateSessionDetailed,
} from "~/lib/session";
import { getUserById } from "~/lib/db-utils";
import type { RouterContextProvider } from "react-router";

/**
 * Authentication result type
 */
export interface AuthResult {
  success: boolean;
  user?: any;
  error?: {
    message: string;
    code: string;
  };
}

/**
 * Common authentication logic
 * Supports two authentication methods:
 * 1. Header authentication (priority) - use ADMIN_AUTH_HEADER and ADMIN_AUTH_SECRET
 * 2. Session authentication (fallback) - use session in Cookie
 */
export const authenticate = async (
  request: Request<unknown, CfProperties<unknown>>,
  context: Readonly<RouterContextProvider>
): Promise<AuthResult> => {
  const { db, sessionKV, cloudflare } = context.get(EnvContext);

  // Get admin authentication configuration from environment variables
  const ADMIN_AUTH_HEADER = cloudflare.env.ADMIN_AUTH_HEADER;
  const ADMIN_AUTH_SECRET = cloudflare.env.ADMIN_AUTH_SECRET;

  // Method 1: Check admin authentication key in request header
  const authAdminHeader = request.headers.get(ADMIN_AUTH_HEADER);
  if (authAdminHeader === ADMIN_AUTH_SECRET) {
    // Header authentication passed, create a virtual admin user object
    const virtualAdminUser = {
      id: "00000000-0000-0000-0000-000000000000", // Virtual UUID
      email: "admin@header.auth",
      name: "Header Admin",
      role: "admin" as const,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return {
      success: true,
      user: virtualAdminUser,
    };
  }

  // Method 2: Use original session validation logic
  // Get session ID from request
  const sessionId = getSessionFromRequest(request);

  if (!sessionId) {
    return {
      success: false,
      error: {
        message: "Unauthorized: No session token",
        code: "UNAUTHORIZED",
      },
    };
  }

  // Validate session, use enhanced version to get detailed result
  const validationResult = await validateSessionDetailed(
    sessionKV as any,
    sessionId
  );

  if (!validationResult.isValid) {
      // Return different error messages based on failure reason
    const reason = validationResult.reason;
    let errorMessage = "Unauthorized: Invalid session";
    let errorCode = "UNAUTHORIZED";

    if (reason === "expired") {
      errorMessage = "Unauthorized: Session expired";
      errorCode = "SESSION_EXPIRED";
    } else if (reason === "not_found") {
      errorMessage = "Unauthorized: Session not found";
      errorCode = "SESSION_NOT_FOUND";
    } else if (reason === "invalid") {
      errorMessage = "Unauthorized: Invalid session";
      errorCode = "SESSION_INVALID";
    }

    return {
      success: false,
      error: {
        message: errorMessage,
        code: errorCode,
      },
    };
  }

  // Get latest user information from database
  const user = await getUserById(db, validationResult.sessionData!.userId);
  if (!user) {
    // User not found, clear session
    await sessionKV.delete(sessionId);
    return {
      success: false,
      error: {
        message: "Unauthorized: User not found",
        code: "USER_NOT_FOUND",
      },
    };
  }

  return {
    success: true,
    user,
  };
};

/**
 * Helper function to set user context
 */
export function setUserContext(
  context: Readonly<RouterContextProvider>,
  user: any
): void {
  context.set(UserContext, user);
}
