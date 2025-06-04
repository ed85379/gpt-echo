// app/page.tsx (for Next.js 13+ App Router)
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/chat'); // Or '/memory', etc.
}