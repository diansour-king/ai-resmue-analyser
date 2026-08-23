"use client";

import Link from "next/link";

import { EmailLinkForm } from "@/components/EmailLinkForm";

export default function LoginPage() {
  return (
    <EmailLinkForm
      mode="login"
      title="Sign in to CareerLayer"
      subtitle="We will email you a link. There is no password to remember or for us to lose."
      footer={
        <p className="text-body-md text-on-surface-variant">
          New here?{" "}
          <Link href="/signup" className="font-semibold text-primary hover:underline">
            Create an account
          </Link>
        </p>
      }
    />
  );
}
