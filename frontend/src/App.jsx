import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleDollarSign,
  FileWarning,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import InvestigationModal from "./components/InvestigationModal";

import "./App.css";


// ============================================================
// API CONFIG
// ============================================================

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


// ============================================================
// HELPERS
// ============================================================

const getValue = (
  object,
  keys,
  fallback = "—"
) => {
  if (!object) {
    return fallback;
  }

  for (const key of keys) {
    if (
      object[key] !== undefined &&
      object[key] !== null &&
      object[key] !== ""
    ) {
      return object[key];
    }
  }

  return fallback;
};


const transactionId = (item) => {
  const value = getValue(
    item,
    [
      "transaction_id",
      "gateway_transaction_id",
    ],
    ""
  );

  return String(value || "").trim();
};


const exceptionType = (item) => {
  return getValue(
    item,
    [
      "exception_type",
      "reconciliation_status",
      "status",
    ],
    "UNKNOWN"
  );
};


const numberFormat = (value) => {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "0";
  }

  return new Intl.NumberFormat(
    "en-IN"
  ).format(number);
};


const money = (value) => {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "₹0.00";
  }

  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }
  ).format(number);
};


const percentage = (value) => {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "0.0%";
  }

  const percent =
    number <= 1
      ? number * 100
      : number;

  return `${percent.toFixed(1)}%`;
};


const severityClass = (severity) => {
  const value = String(
    severity || ""
  ).toUpperCase();

  switch (value) {
    case "CRITICAL":
      return "critical";

    case "HIGH":
      return "high";

    case "MEDIUM":
      return "medium";

    case "LOW":
      return "low";

    default:
      return "default";
  }
};


// ============================================================
// STAT CARD
// ============================================================

function StatCard({
  icon,
  tone,
  label,
  value,
  hint,
}) {
  return (
    <article className="stat-card">

      <div
        className={`stat-icon ${tone}`}
      >
        {icon}
      </div>

      <div className="stat-label">
        {label}
      </div>

      <div className="stat-value">
        {value}
      </div>

      <div className="stat-hint">
        {hint}
      </div>

    </article>
  );
}


// ============================================================
// SEVERITY ROW
// ============================================================

function SeverityRow({
  label,
  value,
  total,
}) {
  const count =
    Number(value || 0);

  const percentageValue =
    total
      ? (count / Number(total)) * 100
      : 0;

  return (
    <div className="severity-row">

      <div className="severity-name">

        <span
          className={`severity-dot ${label.toLowerCase()}`}
        />

        <span>
          {label}
        </span>

      </div>

      <strong>
        {numberFormat(count)}
      </strong>

      <div className="severity-track">

        <div
          className={`severity-fill ${label.toLowerCase()}`}
          style={{
            width: `${Math.min(
              percentageValue,
              100
            )}%`,
          }}
        />

      </div>

      <small>
        {percentageValue.toFixed(1)}%
      </small>

    </div>
  );
}


// ============================================================
// PIPELINE CARD
// ============================================================

function PipelineCard({
  number,
  title,
}) {
  return (
    <div className="pipeline-card">

      <span>
        {number}
      </span>

      <strong>
        {title}
      </strong>

    </div>
  );
}


// ============================================================
// MAIN APP
// ============================================================

function App() {

  const [summary, setSummary] =
    useState(null);

  const [exceptions, setExceptions] =
    useState([]);

  const [
    selectedException,
    setSelectedException,
  ] = useState(null);

  const [
    investigation,
    setInvestigation,
  ] = useState(null);

  const [loading, setLoading] =
    useState(true);

  const [
    detailsLoading,
    setDetailsLoading,
  ] = useState(false);

  const [error, setError] =
    useState("");

  const [
    searchTerm,
    setSearchTerm,
  ] = useState("");

  const [filter, setFilter] =
    useState("ALL");

  const [
    activePage,
    setActivePage,
  ] = useState("dashboard");


  // ==========================================================
  // LOAD DASHBOARD
  // ==========================================================

  const loadDashboard = async () => {

    setLoading(true);
    setError("");

    try {

      const [
        summaryResponse,
        exceptionsResponse,
      ] = await Promise.all([
        axios.get(
          `${API_BASE}/api/summary`
        ),

        axios.get(
          `${API_BASE}/api/exceptions`
        ),
      ]);


      setSummary(
        summaryResponse.data || {}
      );


      const payload =
        exceptionsResponse.data;


      let rows = [];


      if (
        Array.isArray(payload)
      ) {

        rows = payload;

      } else if (
        Array.isArray(
          payload?.exceptions
        )
      ) {

        rows =
          payload.exceptions;

      } else if (
        Array.isArray(
          payload?.data
        )
      ) {

        rows =
          payload.data;
      }


      setExceptions(rows);

    } catch (err) {

      console.error(
        "Dashboard error:",
        err
      );

      setError(
        "Unable to connect to the ReconcileAI backend. Make sure FastAPI is running on port 8000."
      );

      setSummary(
        (current) =>
          current || {}
      );

      setExceptions([]);

    } finally {

      setLoading(false);

    }
  };


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    loadDashboard();
  }, []);


  // ==========================================================
  // OPEN INVESTIGATION
  // ==========================================================

  const openException =
    async (id) => {

      if (!id) {
        return;
      }


      setSelectedException({
        transaction_id: id,
        exception_type: "LOADING",
        severity: "MEDIUM",
      });

      setInvestigation(null);

      setDetailsLoading(true);

      setError("");


      const encodedId =
        encodeURIComponent(id);


      const detailUrl =
        `${API_BASE}/api/exceptions/${encodedId}`;


      const investigationUrl =
        `${API_BASE}/api/investigation/${encodedId}`;


      // ------------------------------------------------------
      // EXCEPTION DETAILS
      // ------------------------------------------------------

      try {

        const response =
          await axios.get(
            detailUrl
          );

        setSelectedException(
          response.data
        );

      } catch (err) {

        console.error(
          "Exception detail failed:",
          err
        );

        setSelectedException(
          (current) => ({
            ...(current || {}),
            transaction_id: id,
          })
        );
      }


      // ------------------------------------------------------
      // AI INVESTIGATION
      // ------------------------------------------------------

      try {

        const response =
          await axios.get(
            investigationUrl
          );

        setInvestigation(
          response.data
        );

      } catch (err) {

        console.warn(
          "AI investigation unavailable:",
          err
        );

        setInvestigation(null);

      } finally {

        setDetailsLoading(false);

      }
    };


  // ==========================================================
  // CLOSE MODAL
  // ==========================================================

  const closeModal = () => {

    setSelectedException(null);

    setInvestigation(null);

    setDetailsLoading(false);
  };


  // ==========================================================
  // FILTERED EXCEPTIONS
  // ==========================================================

  const filteredExceptions =
    useMemo(() => {

      const query =
        searchTerm
          .trim()
          .toLowerCase();


      return exceptions.filter(
        (item) => {

          const id =
            transactionId(item)
              .toLowerCase();


          const type =
            String(
              exceptionType(item)
            ).toLowerCase();


          const severity =
            String(
              getValue(
                item,
                ["severity"],
                ""
              )
            ).toLowerCase();


          const matchesSearch =
            !query ||
            id.includes(query) ||
            type.includes(query) ||
            severity.includes(query);


          const currentSeverity =
            String(
              getValue(
                item,
                ["severity"],
                ""
              )
            ).toUpperCase();


          const matchesFilter =
            filter === "ALL" ||
            currentSeverity === filter;


          return (
            matchesSearch &&
            matchesFilter
          );
        }
      );

    }, [
      exceptions,
      searchTerm,
      filter,
    ]);


  // ==========================================================
  // SUMMARY VALUES
  // ==========================================================

  const total =
    Number(
      getValue(
        summary,
        [
          "total_transactions",
          "total",
        ],
        exceptions.length
      )
    ) ||
    exceptions.length;


  const exceptionCount =
    Number(
      getValue(
        summary,
        [
          "exceptions",
          "exception_count",
        ],
        exceptions.length
      )
    ) ||
    0;


  const reconciled =
    Number(
      getValue(
        summary,
        [
          "reconciled",
          "reconciled_count",
        ],
        Math.max(
          total -
          exceptionCount,
          0
        )
      )
    ) ||
    0;


  const amountAtRisk =
    getValue(
      summary,
      [
        "amount_at_risk",
        "total_amount_at_risk",
      ],
      0
    );


  const aiInvestigations =
    Number(
      getValue(
        summary,
        [
          "ai_investigations",
          "investigations",
        ],
        exceptionCount
      )
    ) ||
    0;


  const autoResolution =
    Number(
      getValue(
        summary,
        [
          "auto_resolution",
          "auto_resolved",
        ],
        0
      )
    ) ||
    0;


  const reconciliationPercentage =
    total
      ? (reconciled / total) *
        100
      : 0;


  // ==========================================================
  // SEVERITY COUNTS
  // ==========================================================

  const severityCounts =
    useMemo(() => {

      const result = {
        CRITICAL: 0,
        HIGH: 0,
        MEDIUM: 0,
        LOW: 0,
      };


      exceptions.forEach(
        (item) => {

          const severity =
            String(
              getValue(
                item,
                ["severity"],
                ""
              )
            ).toUpperCase();


          if (
            result[severity] !==
            undefined
          ) {

            result[severity] += 1;
          }
        }
      );


      return result;

    }, [exceptions]);


  // ==========================================================
  // NAVIGATION
  // ==========================================================

  const navigation = [
    {
      key: "dashboard",
      label: "Dashboard",
      icon: <Activity size={18} />,
    },

    {
      key: "exceptions",
      label: "Exceptions",
      icon: <FileWarning size={18} />,
      count: exceptionCount,
    },

    {
      key: "ai",
      label: "AI Investigations",
      icon: <Sparkles size={18} />,
    },

    {
      key: "reconciliation",
      label: "Reconciliation",
      icon: <CheckCircle2 size={18} />,
    },
  ];


  // ==========================================================
  // LOADING SCREEN
  // ==========================================================

  if (loading) {

    return (
      <div className="loading-screen">

        <div className="loading-logo">
          <ShieldCheck size={34} />
        </div>

        <h1>
          ReconcileAI
        </h1>

        <p>
          Loading reconciliation intelligence...
        </p>

        <div className="loader" />

      </div>
    );
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="app">

      {/* ==================================================== */}
      {/* SIDEBAR */}
      {/* ==================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            <ShieldCheck size={24} />
          </div>

          <div>
            <h1>
              ReconcileAI
            </h1>

            <span>
              Financial Intelligence
            </span>
          </div>

        </div>


        <nav className="main-nav">

          {navigation.map(
            (item) => (

              <button
                key={item.key}
                type="button"
                className={`nav-item ${
                  activePage ===
                  item.key
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setActivePage(
                    item.key
                  )
                }
              >

                {item.icon}

                <span>
                  {item.label}
                </span>

                {item.count !==
                  undefined && (
                  <span className="nav-count">
                    {item.count}
                  </span>
                )}

              </button>
            )
          )}

        </nav>


        <div className="sidebar-bottom">

          <div className="pipeline-title">
            PIPELINE
          </div>

          <div className="pipeline-step">
            <span>01</span>
            Exact Matching
          </div>

          <div className="pipeline-step">
            <span>02</span>
            Fuzzy Matching
          </div>

          <div className="pipeline-step">
            <span>03</span>
            AI Investigation
          </div>

          <div className="pipeline-step">
            <span>04</span>
            Final Decision
          </div>

        </div>

      </aside>


      {/* ==================================================== */}
      {/* MAIN */}
      {/* ==================================================== */}

      <main className="main">

        {/* ERROR */}
        {error && (

          <div className="error-banner">

            <span>
              {error}
            </span>

            <button
              type="button"
              onClick={
                loadDashboard
              }
            >
              Retry
            </button>

          </div>
        )}


        {/* ================================================== */}
        {/* DASHBOARD */}
        {/* ================================================== */}

        {activePage ===
          "dashboard" && (

          <>

            {/* PAGE HEADER */}

            <header className="page-header">

              <div>

                <p className="eyebrow">
                  AUTONOMOUS RECONCILIATION
                </p>

                <h1>
                  Reconciliation Dashboard
                </h1>

                <p>
                  Monitor transactions,
                  exceptions and
                  AI-assisted investigations.
                </p>

              </div>


              <div className="header-actions">

                <div className="health-pill">

                  <span />

                  System Healthy

                </div>


                <button
                  type="button"
                  className="refresh-button"
                  onClick={
                    loadDashboard
                  }
                >

                  <RefreshCw
                    size={15}
                  />

                  Refresh

                </button>

              </div>

            </header>


            {/* KPI CARDS */}

            <section className="stat-grid">

              <StatCard
                icon={
                  <Activity size={18} />
                }
                tone="blue"
                label="Total Transactions"
                value={
                  numberFormat(
                    total
                  )
                }
                hint="Processed transactions"
              />


              <StatCard
                icon={
                  <CheckCircle2
                    size={18}
                  />
                }
                tone="green"
                label="Reconciled"
                value={
                  numberFormat(
                    reconciled
                  )
                }
                hint="Successfully reconciled"
              />


              <StatCard
                icon={
                  <AlertTriangle
                    size={18}
                  />
                }
                tone="amber"
                label="Exceptions"
                value={
                  numberFormat(
                    exceptionCount
                  )
                }
                hint={`${percentage(
                  total
                    ? exceptionCount /
                        total
                    : 0
                )} exception rate`}
              />


              <StatCard
                icon={
                  <CircleDollarSign
                    size={18}
                  />
                }
                tone="red"
                label="Amount at Risk"
                value={
                  money(
                    amountAtRisk
                  )
                }
                hint="Requires investigation"
              />


              <StatCard
                icon={
                  <Sparkles size={18} />
                }
                tone="purple"
                label="AI Investigations"
                value={
                  numberFormat(
                    aiInvestigations
                  )
                }
                hint="Investigated by local AI"
              />


              <StatCard
                icon={
                  <ShieldCheck
                    size={18}
                  />
                }
                tone="slate"
                label="Auto Resolution"
                value={
                  numberFormat(
                    autoResolution
                  )
                }
                hint="Financial actions blocked"
              />

            </section>


            {/* ================================================= */}
            {/* ANALYTICS */}
            {/* ================================================= */}

            <section className="analytics-grid">


              {/* TRANSACTION OUTCOME */}

              <article className="panel health-panel">

                <div className="panel-heading">

                  <div>

                    <p className="eyebrow">
                      RECONCILIATION HEALTH
                    </p>

                    <h2>
                      Transaction Outcome
                    </h2>

                  </div>

                  <CheckCircle2
                    size={19}
                  />

                </div>


                <div className="health-content">

                  <div
                    className="donut"
                    style={{
                      "--progress":
                        `${Math.min(
                          reconciliationPercentage,
                          100
                        )}%`,
                    }}
                  >

                    <div className="donut-inner">

                      <strong>
                        {reconciliationPercentage.toFixed(
                          1
                        )}
                        %
                      </strong>

                      <span>
                        reconciled
                      </span>

                    </div>

                  </div>


                  <div className="health-rows">

                    <div className="health-row">

                      <span>
                        Reconciled
                      </span>

                      <strong>
                        {numberFormat(
                          reconciled
                        )}
                      </strong>

                      <small>
                        {reconciliationPercentage.toFixed(
                          1
                        )}
                        %
                      </small>

                    </div>


                    <div className="health-row">

                      <span>
                        Exceptions
                      </span>

                      <strong>
                        {numberFormat(
                          exceptionCount
                        )}
                      </strong>

                      <small>
                        {(
                          100 -
                          reconciliationPercentage
                        ).toFixed(
                          1
                        )}
                        %
                      </small>

                    </div>


                    <div className="health-row total-row">

                      <span>
                        Total
                      </span>

                      <strong>
                        {numberFormat(
                          total
                        )}
                      </strong>

                      <small />

                    </div>

                  </div>

                </div>

              </article>


              {/* SEVERITY */}

              <article className="panel severity-panel">

                <div className="panel-heading">

                  <div>

                    <p className="eyebrow">
                      RISK DISTRIBUTION
                    </p>

                    <h2>
                      Exception Severity
                    </h2>

                  </div>

                  <AlertTriangle
                    size={19}
                  />

                </div>


                <div className="severity-list">

                  <SeverityRow
                    label="Critical"
                    value={
                      severityCounts.CRITICAL
                    }
                    total={
                      exceptionCount
                    }
                  />

                  <SeverityRow
                    label="High"
                    value={
                      severityCounts.HIGH
                    }
                    total={
                      exceptionCount
                    }
                  />

                  <SeverityRow
                    label="Medium"
                    value={
                      severityCounts.MEDIUM
                    }
                    total={
                      exceptionCount
                    }
                  />

                  <SeverityRow
                    label="Low"
                    value={
                      severityCounts.LOW
                    }
                    total={
                      exceptionCount
                    }
                  />

                </div>

              </article>

            </section>


            {/* EXCEPTIONS */}

            <ExceptionTable
              rows={
                filteredExceptions.slice(
                  0,
                  10
                )
              }
              searchTerm={
                searchTerm
              }
              setSearchTerm={
                setSearchTerm
              }
              filter={filter}
              setFilter={setFilter}
              onInvestigate={
                openException
              }
            />

          </>
        )}


        {/* ================================================== */}
        {/* EXCEPTIONS PAGE */}
        {/* ================================================== */}

        {activePage ===
          "exceptions" && (

          <>

            <header className="page-header compact">

              <div>

                <p className="eyebrow">
                  INVESTIGATION QUEUE
                </p>

                <h1>
                  Exceptions
                </h1>

                <p>
                  Transactions requiring
                  analyst attention.
                </p>

              </div>

            </header>


            <ExceptionTable
              rows={
                filteredExceptions
              }
              searchTerm={
                searchTerm
              }
              setSearchTerm={
                setSearchTerm
              }
              filter={filter}
              setFilter={setFilter}
              onInvestigate={
                openException
              }
            />

          </>
        )}


        {/* ================================================== */}
        {/* AI PAGE */}
        {/* ================================================== */}

        {activePage === "ai" && (

          <>

            <header className="page-header compact">

              <div>

                <p className="eyebrow">
                  AI INVESTIGATION
                </p>

                <h1>
                  AI Investigations
                </h1>

                <p>
                  AI-assisted analysis
                  of reconciliation
                  exceptions.
                </p>

              </div>

            </header>


            <ExceptionTable
              rows={
                filteredExceptions
              }
              searchTerm={
                searchTerm
              }
              setSearchTerm={
                setSearchTerm
              }
              filter={filter}
              setFilter={setFilter}
              onInvestigate={
                openException
              }
            />

          </>
        )}


        {/* ================================================== */}
        {/* RECONCILIATION */}
        {/* ================================================== */}

        {activePage ===
          "reconciliation" && (

          <>

            <header className="page-header compact">

              <div>

                <p className="eyebrow">
                  RECONCILIATION PIPELINE
                </p>

                <h1>
                  Reconciliation
                </h1>

                <p>
                  Monitor the autonomous
                  reconciliation pipeline.
                </p>

              </div>

            </header>


            <section className="panel pipeline-panel">

              <div className="pipeline-grid">

                <PipelineCard
                  number="01"
                  title="Exact Matching"
                />

                <PipelineCard
                  number="02"
                  title="Fuzzy Matching"
                />

                <PipelineCard
                  number="03"
                  title="AI Investigation"
                />

                <PipelineCard
                  number="04"
                  title="Final Decision"
                />

              </div>

            </section>


            <ExceptionTable
              rows={
                filteredExceptions
              }
              searchTerm={
                searchTerm
              }
              setSearchTerm={
                setSearchTerm
              }
              filter={filter}
              setFilter={setFilter}
              onInvestigate={
                openException
              }
            />

          </>
        )}

      </main>


      {/* ==================================================== */}
      {/* INVESTIGATION MODAL */}
      {/* ==================================================== */}

      <InvestigationModal
        selectedException={
          selectedException
        }
        investigation={
          investigation
        }
        detailsLoading={
          detailsLoading
        }
        onClose={
          closeModal
        }
      />

    </div>
  );
}


// ============================================================
// EXCEPTION TABLE
// ============================================================

function ExceptionTable({
  rows,
  searchTerm,
  setSearchTerm,
  filter,
  setFilter,
  onInvestigate,
}) {

  return (
    <section className="panel exception-panel">

      <div className="exception-header">

        <div>

          <p className="eyebrow">
            INVESTIGATION QUEUE
          </p>

          <h2>
            Exceptions
          </h2>

          <p>
            Transactions requiring
            analyst attention.
          </p>

        </div>


        <div className="table-tools">

          <label className="search-box">

            <Search size={15} />

            <input
              type="text"
              value={
                searchTerm
              }
              onChange={(event) =>
                setSearchTerm(
                  event.target.value
                )
              }
              placeholder="Search transaction..."
            />

          </label>


          <select
            value={filter}
            onChange={(event) =>
              setFilter(
                event.target.value
              )
            }
          >

            <option value="ALL">
              All severity
            </option>

            <option value="CRITICAL">
              Critical
            </option>

            <option value="HIGH">
              High
            </option>

            <option value="MEDIUM">
              Medium
            </option>

            <option value="LOW">
              Low
            </option>

          </select>

        </div>

      </div>


      <div className="table-scroll">

        <table className="exception-table">

          <thead>

            <tr>

              <th>
                TRANSACTION
              </th>

              <th>
                EXCEPTION
              </th>

              <th>
                SEVERITY
              </th>

              <th>
                AMOUNT AT RISK
              </th>

              <th>
                CONFIDENCE
              </th>

              <th>
                ACTION
              </th>

            </tr>

          </thead>


          <tbody>

            {rows.length === 0 ? (

              <tr>

                <td
                  colSpan="6"
                  className="empty-state"
                >
                  No exceptions found.
                </td>

              </tr>

            ) : (

              rows.map(
                (item, index) => {

                  const id =
                    transactionId(
                      item
                    ) ||
                    `ROW-${index + 1}`;


                  const severity =
                    getValue(
                      item,
                      ["severity"],
                      "MEDIUM"
                    );


                  const confidence =
                    getValue(
                      item,
                      [
                        "reconciliation_confidence",
                        "confidence",
                        "fuzzy_confidence",
                      ],
                      null
                    );


                  const amount =
                    getValue(
                      item,
                      [
                        "amount_at_risk",
                        "amount_difference",
                      ],
                      0
                    );


                  return (

                    <tr
                      key={`${id}-${index}`}
                    >

                      <td className="transaction-id">
                        {id}
                      </td>


                      <td>
                        {String(
                          exceptionType(
                            item
                          )
                        ).toUpperCase()}
                      </td>


                      <td>

                        <span
                          className={`severity-badge ${severityClass(
                            severity
                          )}`}
                        >
                          {String(
                            severity
                          ).toUpperCase()}
                        </span>

                      </td>


                      <td>
                        {money(
                          amount
                        )}
                      </td>


                      <td>
                        {confidence ===
                        null
                          ? "—"
                          : percentage(
                              confidence
                            )}
                      </td>


                      <td>

                        <button
                          type="button"
                          className="investigate-button"
                          onClick={() =>
                            onInvestigate(
                              id
                            )
                          }
                        >
                          Investigate
                        </button>

                      </td>

                    </tr>
                  );
                }
              )
            )}

          </tbody>

        </table>

      </div>

    </section>
  );
}


export default App;