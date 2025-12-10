# SAP Loading Screen - Visual Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Django Admin Page (change_form.html)                     │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  "Add to SAP" Button                            │     │  │
│  │  │  [Click] ──────────────┐                        │     │  │
│  │  └────────────────────────┼──────────────────────┘     │  │
│  │                            │                              │  │
│  │                            ▼                              │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  JavaScript Event Handler                        │     │  │
│  │  │  - Prevent default navigation                    │     │  │
│  │  │  - Call SAPLoadingScreen.show()                 │     │  │
│  │  │  - Make AJAX POST request                       │     │  │
│  │  └────────────┬──────────────────────┬──────────┘     │  │
│  │               │                      │                  │  │
│  │               ▼                      ▼                  │  │
│  │  ┌──────────────────┐   ┌──────────────────────────┐   │  │
│  │  │  Loading Screen  │   │  AJAX Request to Django  │   │  │
│  │  │  - Overlay       │   │  POST /post-to-sap/      │   │  │
│  │  │  - Spinner       │   │  + CSRF Token            │   │  │
│  │  │  - Progress Bar  │   └───────────┬──────────────┘   │  │
│  │  │  - Timer         │               │                   │  │
│  │  │  - Warning (15s) │               │                   │  │
│  │  └──────────────────┘               │                   │  │
│  └─────────────────────────────────────┼───────────────────┘  │
│                                         │                       │
└─────────────────────────────────────────┼───────────────────────┘
                                          │
                                          │ HTTP POST
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO SERVER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SalesOrderAdmin.post_single_order_to_sap()              │  │
│  │                                                            │  │
│  │  1. Check if already posted                              │  │
│  │  2. Build SAP payload from order data                    │  │
│  │  3. Call SAPClient.post('Orders', payload)               │  │
│  │     └──────────────┬────────────────┘                    │  │
│  │                    │ (10-20 seconds)                      │  │
│  └────────────────────┼─────────────────────────────────────┘  │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                        │ HTTP POST
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SAP BUSINESS ONE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Service Layer API                                        │  │
│  │  fourbtest.vdc.services:50000/b1s/v2/Orders             │  │
│  │                                                            │  │
│  │  1. Validate order data                                  │  │
│  │  2. Create sales order in SAP                            │  │
│  │  3. Generate DocEntry & DocNum                           │  │
│  │  4. Return response                                       │  │
│  │     {                                                     │  │
│  │       "DocEntry": 12345,                                 │  │
│  │       "DocNum": "SO-12345"                               │  │
│  │     }                                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                        │ JSON Response
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO SERVER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SalesOrderAdmin.post_single_order_to_sap()              │  │
│  │                                                            │  │
│  │  4. Store SAP response in database                        │  │
│  │  5. Update order fields:                                  │  │
│  │     - is_posted_to_sap = True                            │  │
│  │     - sap_doc_entry = 12345                              │  │
│  │     - sap_doc_num = "SO-12345"                           │  │
│  │  6. Return JSON response:                                 │  │
│  │     {                                                     │  │
│  │       "success": true,                                    │  │
│  │       "message": "Order posted successfully",            │  │
│  │       "doc_num": "SO-12345"                              │  │
│  │     }                                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                        │ JSON Response
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  JavaScript AJAX Success Handler                          │  │
│  │                                                            │  │
│  │  1. Parse JSON response                                   │  │
│  │  2. Call SAPLoadingScreen.showResult(true, ...)          │  │
│  │     - Hide spinner & progress bar                         │  │
│  │     - Show success icon (✓)                               │  │
│  │     - Display message & DocNum                            │  │
│  │  3. Wait 2 seconds                                        │  │
│  │  4. Reload page: window.location.reload()                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Timeline Diagram

```
Time     User View                Backend Activity              SAP Activity
─────────────────────────────────────────────────────────────────────────────

0.0s     ┌─────────────────┐
         │ [Add to SAP]    │     Click detected
         └─────────────────┘
                │
                ▼
0.1s     ┌─────────────────┐
         │   ⟳  Loading    │     AJAX POST sent ────────────────►
         │   ▓░░░░░░░░░░   │
         │   Elapsed: 0s   │
         └─────────────────┘

1.0s     ┌─────────────────┐                                     Receiving
         │   ⟳  Loading    │     Building payload                request
         │   ▓▓░░░░░░░░░   │
         │   Elapsed: 1s   │
         └─────────────────┘

2.0s     ┌─────────────────┐                                     Validating
         │   ⟳  Loading    │     Waiting for SAP                 data
         │   ▓▓▓░░░░░░░░   │
         │   Elapsed: 2s   │
         └─────────────────┘

5.0s     ┌─────────────────┐                                     Creating
         │   ⟳  Loading    │     Waiting...                      sales
         │   ▓▓▓▓▓░░░░░░   │                                     order
         │   Elapsed: 5s   │
         └─────────────────┘

10.0s    ┌─────────────────┐                                     Processing
         │   ⟳  Loading    │     Still waiting...                document
         │   ▓▓▓▓▓▓▓░░░░   │                                     lines
         │   Elapsed: 10s  │
         └─────────────────┘

15.0s    ┌─────────────────┐                                     Finalizing
         │   ⟳  Loading    │     Still waiting...
         │   ▓▓▓▓▓▓▓▓▓░░   │
         │   Elapsed: 15s  │
         │ ⚠️ Taking       │
         │   longer...     │
         └─────────────────┘

18.0s    ┌─────────────────┐                                     Generating
         │   ⟳  Loading    │     Waiting...                      response
         │   ▓▓▓▓▓▓▓▓▓▓░   │
         │   Elapsed: 18s  │
         │ ⚠️ Taking       │
         │   longer...     │
         └─────────────────┘

20.0s                            SAP responds ◄─────────────────  Response
                                 {DocEntry:12345}                  sent

20.1s                            Saving to DB
                                 Preparing JSON response

20.2s    ┌─────────────────┐
         │       ✓         │     JSON sent to browser ◄─────────
         │    Success!     │
         │  Order posted   │
         │ DocNum: SO-123  │
         └─────────────────┘

22.2s    [Page Reloading...]     Auto-reload triggered


─────────────────────────────────────────────────────────────────────────────
Total:   22 seconds
```

## Error Flow

```
Time     User View                Backend Activity              SAP Activity
─────────────────────────────────────────────────────────────────────────────

0.0s     [Add to SAP] clicked

0.1s     ┌─────────────────┐
         │   ⟳  Loading    │     AJAX POST sent ────────────────►
         │   ▓░░░░░░░░░░   │
         │   Elapsed: 0s   │
         └─────────────────┘

5.0s     ┌─────────────────┐                                     Connection
         │   ⟳  Loading    │     Waiting...                      timeout
         │   ▓▓▓▓▓░░░░░░   │                                     or error
         │   Elapsed: 5s   │
         └─────────────────┘

5.1s                            Error caught
                                 Exception handling
                                 {success: false, error: "..."}

5.2s     ┌─────────────────┐
         │       ✗         │     JSON sent to browser ◄─────────
         │     Error       │
         │  Connection     │
         │   timeout       │
         └─────────────────┘

10.2s    [Overlay Hidden]        Auto-hide after 5 seconds


─────────────────────────────────────────────────────────────────────────────
Total:   10 seconds
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                      Loading Screen Components                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SAPLoadingScreen Object                                         │
│  ├── Properties                                                  │
│  │   ├── overlay: jQuery object                                 │
│  │   ├── startTime: timestamp                                   │
│  │   ├── elapsedTimer: interval ID                              │
│  │   └── timeoutWarningShown: boolean                           │
│  │                                                                │
│  └── Methods                                                     │
│      ├── init()                                                  │
│      │   └── Create HTML, append to body, store reference       │
│      │                                                            │
│      ├── show()                                                  │
│      │   ├── Reset state variables                              │
│      │   ├── Add 'active' class to overlay                      │
│      │   ├── Start elapsed timer                                │
│      │   └── Disable body scrolling                             │
│      │                                                            │
│      ├── hide()                                                  │
│      │   ├── Remove 'active' class                              │
│      │   ├── Stop elapsed timer                                 │
│      │   └── Re-enable scrolling                                │
│      │                                                            │
│      ├── startElapsedTimer()                                    │
│      │   └── setInterval(() => {                                │
│      │       ├── Calculate elapsed seconds                      │
│      │       ├── Update display                                 │
│      │       └── Show warning at 15s                            │
│      │     }, 100)                                               │
│      │                                                            │
│      ├── stopElapsedTimer()                                     │
│      │   └── clearInterval(elapsedTimer)                        │
│      │                                                            │
│      └── showResult(success, message, docNum)                   │
│          ├── Stop progress animation                            │
│          ├── Hide spinner & progress                            │
│          ├── Show result with icon                              │
│          └── If success: reload after 2s                        │
│              If error: hide after 5s                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## State Machine

```
┌─────────────┐
│   INITIAL   │  User on admin page
│   (Hidden)  │
└──────┬──────┘
       │
       │ User clicks "Add to SAP"
       │
       ▼
┌─────────────┐
│   LOADING   │  ◄───┐
│   (Active)  │      │ Timer updates every 100ms
│   0-14s     │  ────┘
└──────┬──────┘
       │
       │ Elapsed >= 15s
       │
       ▼
┌─────────────┐
│  WARNING    │  ◄───┐
│  (Active)   │      │ Timer continues, warning pulses
│   15s+      │  ────┘
└──────┬──────┘
       │
       │ SAP responds (success or error)
       │
       ├───────────────┬───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   SUCCESS   │ │    ERROR    │ │  ALREADY    │
│  (Result)   │ │  (Result)   │ │   POSTED    │
│   ✓ icon    │ │   ✗ icon    │ │   (Error)   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       │ Wait 2s       │ Wait 5s       │ Wait 5s
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   RELOAD    │ │   HIDDEN    │ │   HIDDEN    │
│  (Page)     │ │  (Overlay)  │ │  (Overlay)  │
└─────────────┘ └─────────────┘ └─────────────┘
```

## CSS Animation Timeline

```
Spinner (1s loop, infinite)
─────────────────────────────────────────────────────────►
0°       90°      180°     270°     360°=0°   90°    ...
│───────│────────│────────│────────│────────│────────│
└─ Continuous rotation, 60 FPS


Progress Bar (20s, single run)
─────────────────────────────────────────────────────────►
0%                          60%                      90%
│────────────────────────────│────────────────────────│
0s                          10s                      20s
└─ Width increases from 0% to 90%, then stops


Warning Pulse (1s loop, infinite)
─────────────────────────────────────────────────────────►
opacity:1   opacity:0.7   opacity:1   opacity:0.7   ...
│───────────│─────────────│───────────│─────────────│
0.0s       0.5s         1.0s       1.5s         2.0s
└─ Fades between 100% and 70% opacity


Slide In (0.3s, single run)
─────────────────────────────────────►
translateY:-50px   translateY:0px
opacity:0          opacity:1
│──────────────────│
0.0s              0.3s
└─ Modal entrance animation
```

## Data Flow

```
Database            Django             Browser            SAP
────────            ──────             ───────            ───
   │                   │                   │               │
   │  Load order #32   │                   │               │
   │◄──────────────────┤                   │               │
   │                   │                   │               │
   │  Order data       │                   │               │
   ├──────────────────►│                   │               │
   │                   │                   │               │
   │                   │  Render page      │               │
   │                   ├──────────────────►│               │
   │                   │                   │               │
   │                   │  Click "Add"      │               │
   │                   │◄──────────────────┤               │
   │                   │                   │               │
   │                   │  Show loading     │               │
   │                   │  ──┐              │               │
   │                   │    │ (immediate)  │               │
   │                   │  ◄─┘              │               │
   │                   │                   │               │
   │                   │  Build payload    │               │
   │                   │  ──┐              │               │
   │                   │    │              │               │
   │                   │  ◄─┘              │               │
   │                   │                   │               │
   │                   │  POST /Orders     │               │
   │                   ├───────────────────────────────────►│
   │                   │                   │               │
   │                   │                   │  Processing   │
   │                   │                   │  (10-20s)     │
   │                   │                   │  ──┐          │
   │                   │                   │    │          │
   │                   │                   │  ◄─┘          │
   │                   │                   │               │
   │                   │  Response JSON    │               │
   │                   │◄───────────────────────────────────┤
   │                   │                   │               │
   │  Save response    │                   │               │
   │◄──────────────────┤                   │               │
   │                   │                   │               │
   │  Updated order    │                   │               │
   ├──────────────────►│                   │               │
   │                   │                   │               │
   │                   │  Success JSON     │               │
   │                   ├──────────────────►│               │
   │                   │                   │               │
   │                   │  Show result      │               │
   │                   │  ──┐              │               │
   │                   │    │ (2s delay)   │               │
   │                   │  ◄─┘              │               │
   │                   │                   │               │
   │                   │  Reload page      │               │
   │                   │◄──────────────────┤               │
   │                   │                   │               │
```

---

## Legend

```
Symbols Used:
─────────────
│  Connection/flow
▼  Direction downward
►  Direction right/outward
◄  Direction left/inward
├  Branch point
└  End point
┐┘ Box corners
⟳  Rotating/loading
✓  Success
✗  Error
⚠️  Warning
```
