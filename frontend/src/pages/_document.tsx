// src/pages/_document.tsx
import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Preload critical CSS */}
        <link
          rel="preload"
          href="/_next/static/css/styles.css"
          as="style"
        />
        {/* Add global styles with proper precedence */}
        <style dangerouslySetInnerHTML={{
          __html: `
            /* Force styles to apply - Equal height grid fix */
            .defect-card-container { 
              display: flex; 
              flex-direction: column; 
              height: 100%; 
            }
            .defect-card { 
              flex: 1; 
              display: flex; 
              flex-direction: column; 
            }
            .defect-card-body { 
              flex: 1; 
            }
            .defect-card-actions { 
              margin-top: auto; 
              padding-top: 0.75rem; 
              border-top: 1px solid #e5e7eb; 
            }
            /* Card min-height */
            .card-min-height {
              min-height: 220px;
            }
            /* Equal height grid */
            .equal-height-grid {
              display: grid;
              gap: 1rem;
              grid-auto-rows: 1fr;
            }
            .equal-height-grid > * {
              height: 100%;
            }
          `
        }} />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}