"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { IntegritySummary } from "@/components/IntegritySummary";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { api } from "@/lib/api";
import type { Skill } from "@/lib/types";
import { useResume } from "@/lib/useResume";

export default function ResumeAnalysisPage({
  params,
}: {
  params: Promise<{ resumeId: string }>;
}) {
  const { resumeId } = use(params);
  const { resume, error, reload, isWorking } = useResume(resumeId);
  const [skills, setSkills] = useState<Skill[] | null>(null);

  useEffect(() => {
    if (resume?.state === "completed") api.getSkills(resumeId).then(setSkills).catch(() => null);
  }, [resume?.state, resumeId]);

  const evidenceHref = `/app/resume/${resumeId}/evidence`;

  return (
    <AsyncState loading={!resume && !error} error={error} onRetry={reload}>
      {resume ? (
        <div className="space-y-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-display text-headline-lg-mobile text-on-surface md:text-headline-lg">
                {resume.filename}
              </h1>
              <p className="mt-1 text-body-md text-on-surface-variant">
                {resume.page_count ?? "?"} page(s) · {Math.round(resume.byte_size / 1024)} KB ·
                uploaded {new Date(resume.created_at).toLocaleDateString()}
              </p>
            </div>
            {resume.evidence_available ? (
              <Link
                href={evidenceHref}
                className="rounded-lg bg-primary px-5 py-3 text-label-md text-on-primary"
              >
                Open evidence viewer
              </Link>
            ) : null}
          </div>

          {isWorking || resume.state === "failed" ? (
            <ProcessingStatus state={resume.state} failureCode={resume.failure_code} />
          ) : null}

          {resume.state === "completed" ? (
            <>
              <IntegritySummary
                counts={resume.findings_by_severity}
                evidenceHref={evidenceHref}
              />

              <section aria-labelledby="skills-heading">
                <h2 id="skills-heading" className="font-display text-headline-md text-on-surface">
                  Skills found, and the evidence for them
                </h2>
                <AsyncState
                  loading={skills === null}
                  error={null}
                  isEmpty={skills?.length === 0}
                  emptyTitle="No recognised skills"
                  emptyBody="Nothing in the resume matched the skill vocabulary."
                >
                  <ul className="mt-3 space-y-2">
                    {(skills ?? []).map((skill) => (
                      <li
                        key={skill.skill_id}
                        className="rounded-lg border border-surface-container-high bg-surface-container-lowest p-4"
                      >
                        <div className="flex items-baseline justify-between gap-4">
                          <span className="text-body-md font-semibold text-on-surface">
                            {skill.canonical_name}
                          </span>
                          <span className="text-label-md text-primary">
                            {Math.round(skill.confidence * 100)}%
                          </span>
                        </div>
                        <p className="mt-1 text-caption text-on-surface-variant">
                          {skill.support_count} supporting mention
                          {skill.support_count === 1 ? "" : "s"}
                          {skill.flagged_support_count > 0
                            ? `, ${skill.flagged_support_count} inside flagged text`
                            : ", none flagged"}
                        </p>
                        {skill.evidence[0] ? (
                          <p className="mt-2 border-l-4 border-primary bg-surface pl-3 text-caption italic text-on-surface-variant">
                            “{skill.evidence[0].text.slice(0, 160)}” — page{" "}
                            {skill.evidence[0].page}
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </AsyncState>
              </section>

              <section aria-labelledby="evidence-heading">
                <h2 id="evidence-heading" className="font-display text-headline-md text-on-surface">
                  Evidence
                </h2>
                <p className="mt-2 text-body-md text-on-surface-variant">
                  {resume.evidence_available
                    ? `${resume.pages.length} rendered page(s) available at ${
                        resume.pages[0]?.render_dpi ?? 200
                      } DPI.`
                    : "No rendered pages are available for this resume."}
                </p>
              </section>
            </>
          ) : null}
        </div>
      ) : null}
    </AsyncState>
  );
}
