// The shapes of the JSON our FastAPI backend sends back

export type User = {
  id: string;
  email: string;
  totp_enabled: boolean;
  created_at: string;
};

export type LoginResponse = {
  access_token: string | null;
  token_type: string;
  requires_2fa: boolean;
  challenge_token: string | null;
};

export type TwoFactorSetup = {
  secret: string;
  otpauth_uri: string;
  qr_code_data_uri: string;
};
