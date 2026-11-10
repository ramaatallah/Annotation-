// app/page.tsx — Next.js App Router entry point
// This is a Server Component; it renders HomePage (Client) which
// handles all navigation state client-side.

import HomePage from '@/views/HomePage';

export default function Page() {
  return <HomePage />;
}
