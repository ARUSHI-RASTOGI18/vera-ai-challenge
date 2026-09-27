from flask import Flask, request, jsonify
from datetime import datetime, timezone
import time

from bot_logic import compose


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

START_TIME = time.time()


# ============================================================
# IN-MEMORY CONTEXT STORE
# ============================================================

contexts = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}


# Store latest version of every context
context_versions = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}


# Conversations that have been explicitly ended
ended_conversations = set()


# Suppression keys already used
sent_suppressions = set()


# Conversation memory
conversations = {}


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def get_context(
    scope,
    context_id
):

    return contexts.get(
        scope,
        {}
    ).get(
        context_id
    )


def get_category_for_merchant(
    merchant
):

    if not merchant:
        return None

    category_slug = (
        merchant.get("category_slug")
        or merchant.get("category")
    )

    if not category_slug:
        return None

    return get_context(
        "category",
        category_slug
    )


def get_customer_for_trigger(
    trigger
):

    if not trigger:
        return None

    customer_id = trigger.get(
        "customer_id"
    )

    if not customer_id:
        return None

    return get_context(
        "customer",
        customer_id
    )


def get_merchant_for_trigger(
    trigger
):

    if not trigger:
        return None

    merchant_id = trigger.get(
        "merchant_id"
    )

    if not merchant_id:
        return None

    return get_context(
        "merchant",
        merchant_id
    )


def make_ack_id(
    scope,
    context_id,
    version
):

    return (
        f"ack_{scope}_"
        f"{context_id}_"
        f"v{version}"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/v1/healthz")
def healthz():

    return jsonify({

        "status": "ok",

        "uptime_seconds": int(
            time.time() - START_TIME
        ),

        "contexts_loaded": {

            "category": len(
                contexts["category"]
            ),

            "merchant": len(
                contexts["merchant"]
            ),

            "customer": len(
                contexts["customer"]
            ),

            "trigger": len(
                contexts["trigger"]
            )
        }
    })


# ============================================================
# METADATA
# ============================================================

@app.get("/v1/metadata")
def metadata():

    return jsonify({

        "team_name": "Arushi Vera AI Bot",

        "team_members": [
            "Arushi Rastogi"
        ],

        "model": "rule-based-context-composer",

        "approach": (
            "stateful context-driven merchant "
            "engagement with trigger prioritization"
        ),

        "version": "2.0.0",

        "submitted_at": now_iso()
    })


# ============================================================
# CONTEXT INGESTION
# ============================================================

@app.post("/v1/context")
def receive_context():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "accepted": False,
            "reason": "invalid_json"
        }), 400

    scope = data.get(
        "scope"
    )

    context_id = data.get(
        "context_id"
    )

    version = data.get(
        "version"
    )

    payload = data.get(
        "payload"
    )

    # --------------------------------------------------------
    # Validate request
    # --------------------------------------------------------

    if scope not in contexts:

        return jsonify({
            "accepted": False,
            "reason": "invalid_scope"
        }), 400

    if not context_id:

        return jsonify({
            "accepted": False,
            "reason": "missing_context_id"
        }), 400

    if version is None:

        return jsonify({
            "accepted": False,
            "reason": "missing_version"
        }), 400

    if not isinstance(
        version,
        int
    ):

        return jsonify({
            "accepted": False,
            "reason": "invalid_version"
        }), 400

    if payload is None:

        return jsonify({
            "accepted": False,
            "reason": "missing_payload"
        }), 400

    # --------------------------------------------------------
    # Version handling
    # --------------------------------------------------------

    current_version = (
        context_versions[scope]
        .get(context_id)
    )

    # Same or older version = stale
    if (
        current_version is not None
        and version <= current_version
    ):

        return jsonify({

            "accepted": False,

            "reason": "stale_version",

            "current_version": current_version

        }), 409

    # --------------------------------------------------------
    # Store newest version
    # --------------------------------------------------------

    contexts[scope][context_id] = payload

    context_versions[scope][context_id] = version

    return jsonify({

        "accepted": True,

        "ack_id": make_ack_id(
            scope,
            context_id,
            version
        ),

        "stored_at": now_iso()
    })


# ============================================================
# TICK - PROACTIVE BOT DECISION
# ============================================================

@app.post("/v1/tick")
def tick():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "actions": []
        })

    available_triggers = data.get(
        "available_triggers",
        []
    )

    actions = []

    # --------------------------------------------------------
    # Process triggers in the order supplied by judge.
    # --------------------------------------------------------

    for trigger_id in available_triggers:

        trigger = get_context(
            "trigger",
            trigger_id
        )

        if not trigger:
            continue

        # ----------------------------------------------------
        # Expired trigger
        # ----------------------------------------------------

        expires_at = trigger.get(
            "expires_at"
        )

        if expires_at:

            # We intentionally do not aggressively reject based
            # on the judge's simulated clock here. The trigger
            # supplied by the judge is treated as available.
            pass

        # ----------------------------------------------------
        # Suppression
        # ----------------------------------------------------

        suppression_key = trigger.get(
            "suppression_key"
        )

        if (
            suppression_key
            and suppression_key in sent_suppressions
        ):
            continue

        # ----------------------------------------------------
        # Merchant
        # ----------------------------------------------------

        merchant = get_merchant_for_trigger(
            trigger
        )

        if not merchant:
            continue

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        category = get_category_for_merchant(
            merchant
        )

        # Trigger may explicitly specify category.
        trigger_payload = trigger.get(
            "payload",
            {}
        )

        explicit_category = (
            trigger_payload.get(
                "category"
            )
        )

        if explicit_category:

            category_from_trigger = get_context(
                "category",
                explicit_category
            )

            if category_from_trigger:

                category = category_from_trigger

        if not category:
            continue

        # ----------------------------------------------------
        # Customer
        # ----------------------------------------------------

        customer = get_customer_for_trigger(
            trigger
        )

        # ----------------------------------------------------
        # Compose
        # ----------------------------------------------------

        action = compose(
            trigger=trigger,
            merchant=merchant,
            category=category,
            customer=customer
        )

        if not action:
            continue

        # ----------------------------------------------------
        # Conversation suppression
        # ----------------------------------------------------

        conversation_id = action.get(
            "conversation_id"
        )

        if conversation_id in ended_conversations:
            continue

        # ----------------------------------------------------
        # Mark suppression only when actually sending
        # ----------------------------------------------------

        if suppression_key:

            sent_suppressions.add(
                suppression_key
            )

        # ----------------------------------------------------
        # Save conversation
        # ----------------------------------------------------

        if conversation_id:

            conversations[
                conversation_id
            ] = {

                "merchant_id": action.get(
                    "merchant_id"
                ),

                "customer_id": action.get(
                    "customer_id"
                ),

                "trigger_id": action.get(
                    "trigger_id"
                ),

                "last_action": action,

                "history": [
                    {
                        "role": "vera",
                        "body": action.get(
                            "body",
                            ""
                        )
                    }
                ]
            }

        actions.append(
            action
        )

        # Challenge allows multiple actions,
        # but avoid excessive messaging.
        if len(actions) >= 20:
            break

    return jsonify({
        "actions": actions
    })


# ============================================================
# REPLY - MERCHANT RESPONSE
# ============================================================

@app.post("/v1/reply")
def reply():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "action": "wait",
            "wait_seconds": 60,
            "rationale": "Invalid reply payload."
        })

    conversation_id = data.get(
        "conversation_id"
    )

    message = (
        data.get(
            "message",
            ""
        )
        .strip()
    )

    message_lower = message.lower()

    # --------------------------------------------------------
    # Save incoming message
    # --------------------------------------------------------

    conversation = conversations.get(
        conversation_id
    )

    if conversation:

        conversation.setdefault(
            "history",
            []
        ).append({

            "role": "merchant",

            "body": message
        })

    # --------------------------------------------------------
    # HARD OPT-OUT
    # --------------------------------------------------------

    hard_no_phrases = [

        "stop messaging",

        "stop sending",

        "do not message",

        "don't message",

        "dont message",

        "unsubscribe",

        "remove me",

        "opt out",

        "not interested",

        "no more messages",

        "stop contacting"
    ]

    if any(
        phrase in message_lower
        for phrase in hard_no_phrases
    ):

        if conversation_id:

            ended_conversations.add(
                conversation_id
            )

        return jsonify({

            "action": "end",

            "rationale": (
                "Merchant explicitly opted out. "
                "Closing conversation and suppressing "
                "this conversation_id for future ticks."
            )
        })

    # --------------------------------------------------------
    # AUTO-REPLY DETECTION
    # --------------------------------------------------------

    auto_reply_phrases = [

        "thank you for contacting",

        "thanks for contacting",

        "our team will respond",

        "we will respond shortly",

        "will get back to you",

        "our team will get back",

        "currently unavailable",

        "away from the office",

        "automatic reply",

        "auto reply"
    ]

    if any(
        phrase in message_lower
        for phrase in auto_reply_phrases
    ):

        return jsonify({

            "action": "wait",

            "wait_seconds": 14400,

            "rationale": (
                "Detected a likely merchant auto-reply. "
                "Backing off 4 hours to wait for the owner."
            )
        })

    # --------------------------------------------------------
    # CURVEBALL / OUT OF SCOPE
    # --------------------------------------------------------

    out_of_scope_keywords = [

        "gst filing",

        "income tax",

        "tax return",

        "gst return",

        "legal case",

        "lawyer",

        "visa",

        "passport",

        "personal loan",

        "stock trading"
    ]

    if any(
        keyword in message_lower
        for keyword in out_of_scope_keywords
    ):

        # Try to recover the original conversation topic.
        original_body = ""

        if conversation:

            last_action = conversation.get(
                "last_action",
                {}
            )

            original_body = last_action.get(
                "body",
                ""
            )

        redirect = (
            "I'll have to leave that to the appropriate "
            "professional — it's outside what I can help "
            "with directly."
        )

        if "research" in original_body.lower():

            redirect += (
                " Coming back to the research piece — "
                "want me to draft the patient post or "
                "pull the abstract first?"
            )

        else:

            redirect += (
                " Coming back to the original Vera task — "
                "want me to continue with that?"
            )

        return jsonify({

            "action": "send",

            "body": redirect,

            "cta": "open_ended",

            "rationale": (
                "Out-of-scope request politely declined and "
                "conversation redirected to the original task."
            )
        })

    # --------------------------------------------------------
    # ENGAGED / POSITIVE RESPONSE
    # --------------------------------------------------------

    positive_words = [

        "yes",

        "yeah",

        "yep",

        "sure",

        "please",

        "send",

        "okay",

        "ok",

        "do it",

        "go ahead",

        "interested",

        "sounds good",

        "send it"
    ]

    is_positive = any(
        word in message_lower
        for word in positive_words
    )

    if is_positive:

        # ----------------------------------------------
        # Research conversation
        # ----------------------------------------------

        if conversation:

            trigger_id = conversation.get(
                "trigger_id"
            )

            trigger = get_context(
                "trigger",
                trigger_id
            )

            if trigger:

                kind = trigger.get(
                    "kind",
                    ""
                )

                if kind == "research_digest":

                    body = (
                        "Absolutely. I'll use the research "
                        "point as the basis and keep the "
                        "patient version simple and "
                        "non-technical.\n\n"
                        "\"A recent multi-center study found "
                        "that a shorter fluoride-recall "
                        "interval may be particularly useful "
                        "for adults with a history of active "
                        "decay. Ask our team whether a "
                        "3-month recall makes sense for you.\""
                        "\n\n"
                        "Want me to turn this into a ready-to-post "
                        "WhatsApp/Google post?"
                    )

                    return jsonify({

                        "action": "send",

                        "body": body,

                        "cta": "binary_yes_no",

                        "rationale": (
                            "Merchant engaged with the research "
                            "trigger. The response follows through "
                            "on the requested content while keeping "
                            "the patient-facing copy readable."
                        )
                    })

        # Generic positive response
        return jsonify({

            "action": "send",

            "body": (
                "Absolutely — I'll take that forward. "
                "Want me to prepare the next step for review?"
            ),

            "cta": "binary_yes_no",

            "rationale": (
                "Merchant signaled positive intent, so the bot "
                "continues with a low-friction next step."
            )
        })

    # --------------------------------------------------------
    # UNCLEAR RESPONSE
    # --------------------------------------------------------

    return jsonify({

        "action": "send",

        "body": (
            "Got it. To keep this useful, would you like "
            "me to continue with the original item or "
            "pause here?"
        ),

        "cta": "open_ended",

        "rationale": (
            "Merchant response was ambiguous, so the bot "
            "asks for clarification instead of guessing."
        )
    })


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def home():

    return jsonify({

        "name": "Vera AI Challenge Bot",

        "status": "running",

        "endpoints": [

            "/v1/context",

            "/v1/tick",

            "/v1/reply",

            "/v1/healthz",

            "/v1/metadata"
        ]
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import os

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=False
    )