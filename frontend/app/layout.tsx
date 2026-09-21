import type { Metadata } from "next";
import { IBM_Plex_Mono, Schibsted_Grotesk, Sora } from "next/font/google";
import "./globals.css";
import { themeScript } from "@/components/ThemeToggle";
import { Depth } from "@/components/Depth";

// Geist is one of the three default AI typefaces, alongside Inter and Space
// Grotesk; it reads as "a font nobody chose". A display face with real voice
// paired against a neutral text face does more for the page than any amount
// of colour work.
const display = Sora({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["600", "700"],
});

const sans = Schibsted_Grotesk({
  variable: "--font-sans-ui",
  subsets: ["latin"],
});

// Mono carries most of this product's data, so it is a real reading face,
// not a code-block afterthought.
const mono = IBM_Plex_Mono({
  variable: "--font-mono-ui",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "ContribAI",
  description:
    "Find the open-source issue that is actually right for you. ContribAI reads your GitHub evidence, analyses real issues, and builds a contribution path matched to your skills.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning is correct here, not a papered-over bug: the
    // inline script below deliberately stamps data-theme on this element
    // before React boots, so the server HTML and the hydrated DOM are
    // guaranteed to differ by exactly that attribute. The suppression applies
    // one level deep, to <html> only.
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <head>
        {/* Before first paint, so a saved light theme never flashes dark. */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col">
        <Depth />
        {children}
      </body>
    </html>
  );
}
