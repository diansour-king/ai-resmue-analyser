"use client";

import Link from "next/link";

import { EmailLinkForm } from "@/components/EmailLinkForm";

export default function SignUpPage() {
  return (
    <EmailLinkForm
      mode="signup"
      title="Create your CareerLayer account"
      subtitle="Your email is all we need. We will send a sign-in link to it."
      footer={
        <p className="text-body-md text-on-surface-variant">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-primary hover:underline">
            Sign in
          </Link>
        </p>
      }
    />
  );
}
