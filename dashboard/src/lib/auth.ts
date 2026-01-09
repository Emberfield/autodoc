import { AuthJoyConfig } from "@authjoyio/core";

/**
 * AuthJoy configuration for Autodoc Cloud
 *
 * Environment variables:
 * - NEXT_PUBLIC_AUTHJOY_TENANT_ID: Your AuthJoy tenant ID (UUID)
 * - NEXT_PUBLIC_AUTHJOY_API_KEY: Your AuthJoy API key (aj_live_... or aj_test_...)
 */
export const authConfig: AuthJoyConfig = {
  tenantId: process.env.NEXT_PUBLIC_AUTHJOY_TENANT_ID || "",
  apiKey: process.env.NEXT_PUBLIC_AUTHJOY_API_KEY || "",
  persistence: "local",
};

/**
 * Check if auth is configured (cloud mode)
 */
export function isCloudMode(): boolean {
  return !!(
    process.env.NEXT_PUBLIC_AUTHJOY_TENANT_ID &&
    process.env.NEXT_PUBLIC_AUTHJOY_API_KEY
  );
}
