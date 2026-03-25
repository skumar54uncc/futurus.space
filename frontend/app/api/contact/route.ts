import { NextResponse } from "next/server";
import nodemailer from "nodemailer";

const MAX_LEN = { name: 120, email: 254, subject: 200, message: 10_000 };

function escapeHtml(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const name = typeof body.name === "string" ? body.name.trim() : "";
    const email = typeof body.email === "string" ? body.email.trim() : "";
    const subject =
      typeof body.subject === "string" && body.subject.trim()
        ? body.subject.trim()
        : "Futurus contact form";
    const message = typeof body.message === "string" ? body.message.trim() : "";

    if (!name || name.length > MAX_LEN.name) {
      return NextResponse.json({ error: "Invalid name." }, { status: 400 });
    }
    if (!email || email.length > MAX_LEN.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json({ error: "Invalid email." }, { status: 400 });
    }
    if (!message || message.length > MAX_LEN.message) {
      return NextResponse.json({ error: "Invalid message." }, { status: 400 });
    }
    if (subject.length > MAX_LEN.subject) {
      return NextResponse.json({ error: "Subject too long." }, { status: 400 });
    }

    const host = process.env.SMTP_HOST;
    const user = process.env.SMTP_USER;
    const pass = process.env.SMTP_PASS;
    const to = process.env.CONTACT_TO_EMAIL || user;
    const from = process.env.SMTP_FROM || user;

    if (!host || !user || !pass || !to) {
      return NextResponse.json(
        {
          error:
            "Email is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS, and CONTACT_TO_EMAIL (or rely on SMTP_USER as recipient) in your environment.",
        },
        { status: 503 }
      );
    }

    const port = Number(process.env.SMTP_PORT || "587");
    const secure = process.env.SMTP_SECURE === "true" || port === 465;

    const transporter = nodemailer.createTransport({
      host,
      port,
      secure,
      auth: { user, pass },
    });

    const safeName = escapeHtml(name);
    const safeEmail = escapeHtml(email);
    const safeMsg = escapeHtml(message).replace(/\n/g, "<br/>");

    const fromAddr = from || user;

    await transporter.sendMail({
      from: fromAddr.includes("<") ? fromAddr : `"Futurus contact" <${fromAddr}>`,
      to,
      replyTo: email,
      subject: `[Futurus] ${subject}`,
      text: `From: ${name} <${email}>\n\n${message}`,
      html: `<p><strong>From:</strong> ${safeName} &lt;${safeEmail}&gt;</p><p><strong>Message:</strong></p><p>${safeMsg}</p>`,
    });

    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error("contact mail error", e);
    return NextResponse.json({ error: "Failed to send email." }, { status: 500 });
  }
}
