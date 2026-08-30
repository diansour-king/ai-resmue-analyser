import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../AppShell";
import { EmailLinkForm } from "../EmailLinkForm";
import VerifyPage from "@/app/auth/verify/page";
import { ApiError, api } from "@/lib/api";

const replaceMock = vi.fn();
const pushMock = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
    back: vi.fn(),
  }),
  usePathname: () => "/app",
  useSearchParams: () => mockSearchParams,
}));

afterEach(() => {
  vi.restoreAllMocks();
  replaceMock.mockClear();
  pushMock.mockClear();
  mockSearchParams = new URLSearchParams();
});

describe("Authentication UI & Session Hardening", () => {
  describe("EmailLinkForm (Login & Signup)", () => {
    it("submits login request and displays confirmation with dev link in development mode", async () => {
      vi.spyOn(api, "logIn").mockResolvedValue({
        sent: true,
        login_url: "/auth/verify?token=test-dev-token-123",
      });

      render(
        <EmailLinkForm
          mode="login"
          title="Sign in to CareerLayer"
          subtitle="We will email you a link."
          footer={<a href="/signup">Sign up</a>}
        />
      );

      const input = screen.getByLabelText(/email/i);
      await userEvent.type(input, "alex@example.com");
      fireEvent.click(screen.getByRole("button", { name: /email me a link/i }));

      expect(await screen.findByText(/Check/i)).toHaveTextContent("alex@example.com");
      expect(screen.getByText(/Development link:/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Development link:/i })).toHaveAttribute(
        "href",
        "/auth/verify?token=test-dev-token-123"
      );
    });

    it("does not expose development link when API returns null login_url in production", async () => {
      vi.spyOn(api, "logIn").mockResolvedValue({
        sent: true,
        login_url: null,
      });

      render(
        <EmailLinkForm
          mode="login"
          title="Sign in to CareerLayer"
          subtitle="We will email you a link."
          footer={<a href="/signup">Sign up</a>}
        />
      );

      const input = screen.getByLabelText(/email/i);
      await userEvent.type(input, "prod-user@example.com");
      fireEvent.click(screen.getByRole("button", { name: /email me a link/i }));

      expect(await screen.findByText(/Check/i)).toHaveTextContent("prod-user@example.com");
      expect(screen.queryByText(/Development link:/i)).not.toBeInTheDocument();
    });

    it("submits signup request correctly", async () => {
      const signUpSpy = vi.spyOn(api, "signUp").mockResolvedValue({
        sent: true,
        login_url: "/auth/verify?token=signup-token-456",
      });

      render(
        <EmailLinkForm
          mode="signup"
          title="Create an account"
          subtitle="Start your career intelligence journey."
          footer={<a href="/login">Sign in</a>}
        />
      );

      const input = screen.getByLabelText(/email/i);
      await userEvent.type(input, "newuser@example.com");
      fireEvent.click(screen.getByRole("button", { name: /email me a link/i }));

      expect(signUpSpy).toHaveBeenCalledWith("newuser@example.com");
      expect(await screen.findByText(/Check/i)).toHaveTextContent("newuser@example.com");
    });

    it("displays error message when login fails", async () => {
      vi.spyOn(api, "logIn").mockRejectedValue(
        new ApiError(400, "invalid_request", "Please provide a valid email.", "req-400")
      );

      render(
        <EmailLinkForm
          mode="login"
          title="Sign in"
          subtitle="Subtitle"
          footer={<span>Footer</span>}
        />
      );

      await userEvent.type(screen.getByLabelText(/email/i), "bad@example.com");
      fireEvent.click(screen.getByRole("button", { name: /email me a link/i }));

      expect(await screen.findByRole("alert")).toHaveTextContent("Please provide a valid email.");
    });
  });

  describe("VerifyPage (Magic-link token verification)", () => {
    it("shows error when token param is missing", async () => {
      mockSearchParams = new URLSearchParams();
      render(<VerifyPage />);

      expect(await screen.findByText(/That link is missing its token/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Request a new link/i })).toHaveAttribute(
        "href",
        "/login"
      );
    });

    it("verifies token and redirects to /app for onboarded user", async () => {
      mockSearchParams = new URLSearchParams({ token: "valid-token-abc" });
      vi.spyOn(api, "verify").mockResolvedValue({
        user_id: "u-1",
        email: "alex@example.com",
        display_name: "Alex",
        onboarded: true,
      });

      render(<VerifyPage />);

      await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/app");
      });
    });

    it("verifies token and redirects to /app/onboarding for non-onboarded user", async () => {
      mockSearchParams = new URLSearchParams({ token: "valid-token-new" });
      vi.spyOn(api, "verify").mockResolvedValue({
        user_id: "u-2",
        email: "new@example.com",
        display_name: null,
        onboarded: false,
      });

      render(<VerifyPage />);

      await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/app/onboarding");
      });
    });

    it("shows expired message when token verification fails", async () => {
      mockSearchParams = new URLSearchParams({ token: "expired-token-xyz" });
      vi.spyOn(api, "verify").mockRejectedValue(
        new ApiError(400, "invalid_link", "That sign-in link is no longer valid.", "req-inv")
      );

      render(<VerifyPage />);

      expect(await screen.findByText(/Link expired/i)).toBeInTheDocument();
      expect(screen.getByText(/That sign-in link is no longer valid/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Request a new link/i })).toHaveAttribute(
        "href",
        "/login"
      );
    });
  });

  describe("AppShell (Session validation & Logout)", () => {
    it("renders authenticated identity in header", async () => {
      vi.spyOn(api, "me").mockResolvedValue({
        user_id: "u-1",
        email: "alex@example.com",
        display_name: "Alex Johnson",
        onboarded: true,
      });

      render(
        <AppShell>
          <div>Protected Content</div>
        </AppShell>
      );

      expect(await screen.findByText("Alex Johnson")).toBeInTheDocument();
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("redirects unauthenticated user to /login", async () => {
      vi.spyOn(api, "me").mockRejectedValue(
        new ApiError(401, "unauthenticated", "Sign in to continue.", "req-unauth")
      );

      render(
        <AppShell>
          <div>Protected Content</div>
        </AppShell>
      );

      await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/login");
      });
    });

    it("logs out user and redirects to home on sign out button click", async () => {
      vi.spyOn(api, "me").mockResolvedValue({
        user_id: "u-1",
        email: "alex@example.com",
        display_name: "Alex",
        onboarded: true,
      });
      const logOutSpy = vi.spyOn(api, "logOut").mockResolvedValue(undefined);

      render(
        <AppShell>
          <div>Dashboard</div>
        </AppShell>
      );

      expect(await screen.findByText("Alex")).toBeInTheDocument();
      const signOutButton = screen.getByRole("button", { name: /sign out/i });
      fireEvent.click(signOutButton);

      await waitFor(() => {
        expect(logOutSpy).toHaveBeenCalled();
        expect(replaceMock).toHaveBeenCalledWith("/");
      });
    });
  });
});
