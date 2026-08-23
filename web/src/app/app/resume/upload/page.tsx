"use client";

import { useRouter } from "next/navigation";

import { UploadDropzone } from "@/components/UploadDropzone";

export default function UploadPage() {
  const router = useRouter();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-display text-headline-lg-mobile text-on-surface md:text-headline-lg">
        Upload your resume
      </h1>
      <p className="mt-2 max-w-xl text-body-md text-on-surface-variant">
        CareerLayer reads the document twice: once the way a machine reads it, and once the way
        you see it. Anything that differs between the two is reported for you to review.
      </p>
      <div className="mt-8">
        <UploadDropzone
          onUploaded={(accepted) => router.push(`/app/resume/${accepted.resume_id}`)}
        />
      </div>
      <p className="mt-8 text-caption text-on-surface-variant">
        Findings are advisory and always shown to a person. CareerLayer never rejects a
        candidate and never rewrites a resume.
      </p>
    </div>
  );
}
