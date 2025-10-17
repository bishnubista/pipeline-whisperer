import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN_NEXTJS,

  tracesSampleRate: 1.0,

  debug: false,

  environment: process.env.SENTRY_ENVIRONMENT || 'development',
});
