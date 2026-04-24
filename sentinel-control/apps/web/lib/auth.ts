export interface UserContext {
  userId: string;
  email?: string;
  source: "local" | "header" | "supabase";
  authenticated: boolean;
}

export class AuthRequiredError extends Error {
  constructor(message = "Authentication required.") {
    super(message);
    this.name = "AuthRequiredError";
  }
}

const LOCAL_USER_ID = "local_user";

function requireAuth() {
  return process.env.SENTINEL_REQUIRE_AUTH === "true";
}

function localUser(): UserContext {
  return {
    userId: process.env.SENTINEL_LOCAL_USER_ID || LOCAL_USER_ID,
    source: "local",
    authenticated: false,
  };
}

async function supabaseUserFromToken(token: string): Promise<UserContext | null> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;

  const response = await fetch(`${url.replace(/\/$/, "")}/auth/v1/user`, {
    method: "GET",
    headers: {
      apikey: anonKey,
      authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!response.ok) return null;
  const user = await response.json() as { id?: string; email?: string };
  if (!user.id) return null;
  return {
    userId: user.id,
    email: user.email,
    source: "supabase",
    authenticated: true,
  };
}

export async function getRequestUser(request?: Request): Promise<UserContext> {
  const headerUserId = request?.headers.get("x-sentinel-user-id")?.trim();
  if (headerUserId && !requireAuth()) {
    return {
      userId: headerUserId,
      source: "header",
      authenticated: false,
    };
  }

  const authHeader = request?.headers.get("authorization") || "";
  const token = authHeader.toLowerCase().startsWith("bearer ") ? authHeader.slice(7).trim() : "";
  if (token) {
    const user = await supabaseUserFromToken(token);
    if (user) return user;
  }

  if (requireAuth()) {
    throw new AuthRequiredError();
  }

  return localUser();
}
