import { useEffect } from "react";

import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  FileWarning,
  GitCompare,
  LockKeyhole,
  X,
} from "lucide-react";

import "./InvestigationModal.css";


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

  return String(
    getValue(
      item,
      [
        "transaction_id",
        "gateway_transaction_id",
      ],
      ""
    ) || ""
  ).trim();

};


const money = (value) => {

  const number =
    Number(value);

  if (
    !Number.isFinite(number)
  ) {
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

  const number =
    Number(value);

  if (
    !Number.isFinite(number)
  ) {
    return "—";
  }

  const percent =
    number <= 1
      ? number * 100
      : number;

  return `${percent.toFixed(
    1
  )}%`;
};


const severityClass = (
  severity
) => {

  const value =
    String(
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
// DETAIL
// ============================================================

function Detail({
  label,
  value,
}) {

  return (
    <div className="detail">

      <span>
        {label}
      </span>

      <strong>
        {
          value ===
            undefined ||
          value === null ||
          value === ""
            ? "—"
            : String(value)
        }
      </strong>

    </div>
  );
}


// ============================================================
// MODAL
// ============================================================

function InvestigationModal({
  selectedException,
  investigation,
  detailsLoading,
  onClose,
}) {


  // ==========================================================
  // ESCAPE
  // ==========================================================

  useEffect(() => {

    if (
      !selectedException
    ) {
      return undefined;
    }


    const handleKeyDown =
      (event) => {

        if (
          event.key ===
          "Escape"
        ) {
          onClose();
        }

      };


    document.addEventListener(
      "keydown",
      handleKeyDown
    );


    const previousOverflow =
      document.body.style.overflow;


    document.body.style.overflow =
      "hidden";


    return () => {

      document.removeEventListener(
        "keydown",
        handleKeyDown
      );

      document.body.style.overflow =
        previousOverflow;

    };

  }, [
    selectedException,
    onClose,
  ]);


  // ==========================================================
  // NOTHING SELECTED
  // ==========================================================

  if (
    !selectedException
  ) {
    return null;
  }


  // ==========================================================
  // VALUES
  // ==========================================================

  const id =
    transactionId(
      selectedException
    ) ||
    "Transaction";


  const severity =
    getValue(
      selectedException,
      ["severity"],
      "N/A"
    );


  const exceptionType =
    getValue(
      selectedException,
      [
        "exception_type",
        "reconciliation_status",
        "status",
      ],
      "UNKNOWN"
    );


  const confidence =
    getValue(
      selectedException,
      [
        "reconciliation_confidence",
        "confidence",
        "fuzzy_confidence",
      ],
      null
    );


  const amount =
    getValue(
      selectedException,
      [
        "amount_at_risk",
        "amount_difference",
      ],
      0
    );


  const investigationStatus =
    getValue(
      investigation,
      [
        "ai_status",
        "status",
      ],
      "SUCCESS"
    );


  const aiConfidence =
    getValue(
      investigation,
      [
        "confidence",
        "ai_confidence",
        "reconciliation_confidence",
      ],
      confidence
    );


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div
      className="investigation-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="investigation-title"
      onMouseDown={(event) => {

        if (
          event.target ===
          event.currentTarget
        ) {
          onClose();
        }

      }}
    >

      <section
        className="investigation-modal"
        onMouseDown={(event) =>
          event.stopPropagation()
        }
      >


        {/* ================================================== */}
        {/* HEADER */}
        {/* ================================================== */}

        <header className="modal-header">

          <div className="modal-header-left">

            <div className="modal-icon">
              <Brain size={21} />
            </div>


            <div>

              <p className="panel-label">
                EXCEPTION INVESTIGATION
              </p>

              <h2 id="investigation-title">
                {id}
              </h2>

            </div>

          </div>


          <button
            type="button"
            className="close-button"
            aria-label="Close investigation"
            onClick={onClose}
          >
            <X size={19} />
          </button>

        </header>


        {/* ================================================== */}
        {/* LOADING */}
        {/* ================================================== */}

        {detailsLoading ? (

          <div className="modal-loading">

            <div className="modal-spinner" />

            <strong>
              Loading investigation...
            </strong>

            <span>
              Retrieving exception
              evidence and AI analysis.
            </span>

          </div>

        ) : (

          <div className="modal-content">


            {/* ============================================== */}
            {/* EXCEPTION */}
            {/* ============================================== */}

            <section className="detail-card">

              <div className="detail-title">

                <AlertTriangle
                  size={18}
                />

                Exception Details

              </div>


              <div className="detail-grid">

                <Detail
                  label="Transaction"
                  value={id}
                />

                <Detail
                  label="Exception Type"
                  value={exceptionType}
                />

                <Detail
                  label="Severity"
                  value={severity}
                />

                <Detail
                  label="Amount at Risk"
                  value={money(amount)}
                />

                <Detail
                  label="Confidence"
                  value={percentage(
                    confidence
                  )}
                />

                <Detail
                  label="Reconciliation Method"
                  value={getValue(
                    selectedException,
                    [
                      "reconciliation_method",
                      "match_method",
                    ],
                    "—"
                  )}
                />

                <Detail
                  label="Bank Reference"
                  value={getValue(
                    selectedException,
                    [
                      "bank_reference",
                    ],
                    "—"
                  )}
                />

                <Detail
                  label="Status"
                  value={getValue(
                    selectedException,
                    [
                      "reconciliation_status",
                      "status",
                    ],
                    "REVIEW"
                  )}
                />

              </div>


              <div className="exception-explanation">

                <span>
                  Exception Explanation
                </span>

                <p>
                  {getValue(
                    selectedException,
                    [
                      "explanation",
                      "reason",
                      "reconciliation_reason",
                      "ai_likely_cause",
                    ],
                    "No additional deterministic explanation was provided."
                  )}
                </p>

              </div>


              <div
                className={`modal-severity ${severityClass(
                  severity
                )}`}
              >

                <span className="severity-dot" />

                {String(
                  severity
                ).toUpperCase()}

                {" "}PRIORITY

              </div>

            </section>


            {/* ============================================== */}
            {/* AI */}
            {/* ============================================== */}

            <section className="detail-card ai-card">

              <div className="detail-title">

                <Brain size={18} />

                AI Investigation

              </div>


              {investigation ? (

                <>

                  <div className="ai-status-row">

                    <div>

                      <span>
                        AI Status
                      </span>

                      <strong>
                        {String(
                          investigationStatus
                        ).toUpperCase()}
                      </strong>

                    </div>


                    <div>

                      <span>
                        Evidence Confidence
                      </span>

                      <strong>
                        {percentage(
                          aiConfidence
                        )}
                      </strong>

                    </div>


                    <div>

                      <span>
                        Human Review
                      </span>

                      <strong className="review-required">

                        <LockKeyhole
                          size={14}
                        />

                        Required

                      </strong>

                    </div>

                  </div>


                  <div className="detail-text">

                    <strong>
                      Likely Cause
                    </strong>

                    <p>

                      {getValue(
                        investigation,
                        [
                          "likely_cause",
                          "ai_likely_cause",
                          "cause",
                        ],
                        getValue(
                          selectedException,
                          [
                            "ai_likely_cause",
                          ],
                          "No likely cause was provided."
                        )
                      )}

                    </p>

                  </div>


                  <div className="detail-text">

                    <strong>
                      Reasoning Summary
                    </strong>

                    <p>

                      {getValue(
                        investigation,
                        [
                          "reasoning_summary",
                          "reasoning",
                          "ai_reasoning",
                        ],
                        "No additional reasoning was provided."
                      )}

                    </p>

                  </div>


                  <div className="detail-text">

                    <strong>
                      AI Recommendation
                    </strong>

                    <p>

                      {getValue(
                        investigation,
                        [
                          "recommended_action",
                        ],
                        getValue(
                          selectedException,
                          [
                            "recommended_action",
                          ],
                          "Manual review required."
                        )
                      )}

                    </p>

                  </div>


                  <div className="ai-safety-note">

                    <LockKeyhole
                      size={16}
                    />

                    <span>
                      AI provides investigation
                      assistance only. It cannot
                      authorize financial resolution.
                    </span>

                  </div>

                </>

              ) : (

                <div className="ai-unavailable">

                  <FileWarning
                    size={22}
                  />

                  <div>

                    <strong>
                      AI investigation unavailable
                    </strong>

                    <p>
                      The exception was loaded,
                      but AI investigation data
                      could not be retrieved
                      for this transaction.
                    </p>

                  </div>

                </div>

              )}

            </section>


            {/* ============================================== */}
            {/* FINAL DECISION */}
            {/* ============================================== */}

            <section className="detail-card decision-card">

              <div className="detail-title">

                <CheckCircle2
                  size={18}
                />

                Final Decision

              </div>


              <div className="decision-box">

                <div>

                  <span>
                    Decision
                  </span>

                  <strong>
                    {getValue(
                      selectedException,
                      [
                        "final_decision",
                      ],
                      "MANUAL_REVIEW"
                    )}
                  </strong>

                </div>


                <div>

                  <span>
                    Recommended Action
                  </span>

                  <strong>
                    {getValue(
                      selectedException,
                      [
                        "recommended_action",
                      ],
                      "Human review required."
                    )}
                  </strong>

                </div>

              </div>


              <div className="decision-note">

                <GitCompare
                  size={16}
                />

                <span>
                  Financial actions remain
                  blocked until a human reviewer
                  completes the final decision.
                </span>

              </div>

            </section>

          </div>
        )}


        {/* ================================================== */}
        {/* FOOTER */}
        {/* ================================================== */}

        <footer className="modal-footer">

          <div className="footer-security">

            <LockKeyhole
              size={14}
            />

            Human review required

          </div>


          <button
            type="button"
            className="modal-close-action"
            onClick={onClose}
          >
            Close
          </button>

        </footer>

      </section>

    </div>
  );
}


export default InvestigationModal;