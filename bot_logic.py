import json

from pathlib import Path





# ============================================================

# VERA AI CHALLENGE

# BOT LOGIC ENGINE

# ============================================================



BASE_DIR = Path(__file__).resolve().parent

EXPANDED_DIR = BASE_DIR / "expanded"





# ============================================================

# 1. LOAD DATASET

# ============================================================



def load_json_folder(folder_name):



    folder = EXPANDED_DIR / folder_name



    data = {}



    if not folder.exists():

        print(f"WARNING: Folder not found: {folder}")

        return data



    for file_path in folder.glob("*.json"):



        try:



            with open(

                file_path,

                "r",

                encoding="utf-8"

            ) as file:



                item = json.load(file)



            # ------------------------------------------------

            # IMPORTANT DATASET ID RULES

            # ------------------------------------------------



            if folder_name == "triggers":



                item_id = item.get("id")



            elif folder_name == "merchants":



                item_id = item.get("merchant_id")



            elif folder_name == "customers":



                item_id = item.get("customer_id")



            elif folder_name == "categories":



                item_id = item.get("slug")



            else:



                item_id = (

                    item.get("id")

                    or item.get("merchant_id")

                    or item.get("customer_id")

                    or item.get("slug")

                )



            if item_id:



                data[item_id] = item



        except json.JSONDecodeError as error:



            print(

                f"JSON ERROR in {file_path.name}: {error}"

            )



        except Exception as error:



            print(

                f"ERROR loading {file_path.name}: {error}"

            )



    return data





# Load all contexts

CATEGORIES = load_json_folder("categories")

MERCHANTS = load_json_folder("merchants")

CUSTOMERS = load_json_folder("customers")

TRIGGERS = load_json_folder("triggers")





# ============================================================

# 2. GET CONTEXT

# ============================================================



def get_category(category_slug):



    return CATEGORIES.get(

        category_slug,

        {}

    )





def get_merchant(merchant_id):



    return MERCHANTS.get(

        merchant_id,

        {}

    )





def get_customer(customer_id):



    return CUSTOMERS.get(

        customer_id,

        {}

    )





def get_trigger(trigger_id):



    return TRIGGERS.get(

        trigger_id,

        {}

    )





# ============================================================

# 3. DIGEST LOOKUP

# ============================================================



def get_digest_item(

    category,

    item_id

):



    digest = category.get(

        "digest",

        []

    )



    if not isinstance(

        digest,

        list

    ):

        return {}



    for item in digest:



        if item.get("id") == item_id:



            return item



    return {}





# ============================================================

# 4. MERCHANT OFFERS

# ============================================================



def get_active_offers(

    merchant

):



    offers = merchant.get(

        "offers",

        []

    )



    if not isinstance(

        offers,

        list

    ):

        return []



    return [

        offer

        for offer in offers

        if offer.get("status") == "active"

    ]





def get_best_offer(

    merchant

):



    offers = get_active_offers(

        merchant

    )



    if not offers:

        return None



    return offers[0]





# ============================================================

# 5. BASIC HELPERS

# ============================================================



def merchant_first_name(

    merchant

):



    identity = merchant.get(

        "identity",

        {}

    )



    first_name = identity.get(

        "owner_first_name"

    )



    if first_name:



        return first_name



    name = identity.get(

        "name",

        "there"

    )



    if isinstance(

        name,

        str

    ):



        words = name.split()



        if words:



            return words[0]



    return "there"





def merchant_name(

    merchant

):



    identity = merchant.get(

        "identity",

        {}

    )



    return identity.get(

        "name",

        "your business"

    )





def make_conversation_id(

    trigger,

    merchant,

    customer=None

):



    merchant_id = merchant.get(

        "merchant_id",

        "merchant"

    )



    trigger_id = trigger.get(

        "id",

        "trigger"

    )



    if customer:



        customer_id = customer.get(

            "customer_id",

            "customer"

        )



        return (

            f"conv_{merchant_id}_"

            f"{customer_id}_"

            f"{trigger_id}"

        )



    return (

        f"conv_{merchant_id}_"

        f"{trigger_id}"

    )





# ============================================================

# 6. ACTION BUILDER

# ============================================================



def build_action(

    trigger,

    merchant,

    body,

    template_name,

    rationale,

    customer=None,

    send_as="vera",

    cta="open_ended",

    template_params=None

):



    if template_params is None:



        template_params = []



    return {



        "action": "send",



        "conversation_id": make_conversation_id(

            trigger,

            merchant,

            customer

        ),



        "merchant_id": merchant.get(

            "merchant_id"

        ),



        "customer_id": (

            customer.get("customer_id")

            if customer

            else None

        ),



        "send_as": send_as,



        "trigger_id": trigger.get(

            "id"

        ),



        "template_name": template_name,



        "template_params": template_params,



        "body": body,



        "cta": cta,



        "suppression_key": trigger.get(

            "suppression_key"

        ),



        "rationale": rationale

    }





# ============================================================


# ============================================================
# 7A. CONTEXT-AWARE PRESENTATION HELPERS
# ============================================================

def category_slug(category):
    return str(category.get("slug", "")).lower().strip()

def merchant_salutation(merchant, category):
    first = merchant_first_name(merchant)
    if category_slug(category) in {"dentists", "doctors", "clinics", "healthcare"}:
        return f"Dr. {first}"
    return first

def payload_value(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return None

def human_number(value):
    try:
        return f"{value:,}" if isinstance(value, int) else str(value)
    except Exception:
        return str(value)

def percent_change(delta):
    try:
        value = float(delta)
        return abs(value * 100 if abs(value) <= 1 else value)
    except Exception:
        return None

def category_action_phrase(category):
    return {
        "dentists": "a patient-facing update",
        "pharmacies": "a practical customer update",
        "gyms": "a member-facing action",
        "salons": "a customer-facing offer",
        "restaurants": "a customer-facing promotion",
    }.get(category_slug(category), "a customer-facing action")

def best_offer_label(merchant):
    offer = get_best_offer(merchant)
    if not offer:
        return None
    title, price = offer.get("title"), offer.get("price")
    if title and price is not None:
        return f"{title} ({price})"
    return title

def merchant_context_fact(merchant):
    perf = merchant.get("performance", {}) or {}
    offer = get_best_offer(merchant)
    if perf.get("views") is not None and perf.get("calls") is not None:
        return f"{human_number(perf['views'])} views and {human_number(perf['calls'])} calls in the last 30 days"
    if perf.get("views") is not None:
        return f"{human_number(perf['views'])} views in the last 30 days"
    if offer and offer.get("title"):
        return f"your active offer, {offer.get('title')}"
    return None

def trigger_fact(payload):
    for key in ["title","reason","message","summary","event","metric","delta_pct","delta",
                "deadline_iso","days_remaining","count","threshold","value","theme",
                "service","offer","action","date","last_visit","last_visit_days","trial","segment"]:
        if payload.get(key) is not None and payload.get(key) != "":
            return payload.get(key)
    return None

# 7. RESEARCH DIGEST

# ============================================================



def compose_research_digest(

    trigger,

    merchant,

    category,

    customer=None

):



    payload = trigger.get(

        "payload",

        {}

    )



    item_id = payload.get(

        "top_item_id"

    )



    item = get_digest_item(

        category,

        item_id

    )



    if not item:



        return None



    trial_n = item.get(

        "trial_n"

    )



    source = item.get(

        "source",

        ""

    )



    summary = item.get(

        "summary",

        ""

    )



    patient_segment = item.get(

        "patient_segment"

    )



    customer_aggregate = merchant.get(

        "customer_aggregate",

        {}

    )



    high_risk_count = customer_aggregate.get(

        "high_risk_adult_count"

    )



    first_name = merchant_first_name(

        merchant

    )



    # --------------------------------------------------------

    # HIGH-VALUE PERSONALIZED CASE

    # --------------------------------------------------------



    if (

        patient_segment == "high_risk_adults"

        and high_risk_count

        and trial_n

    ):



        body = (

            f"Dr. {first_name}, JIDA's Oct issue landed. "

            f"One item relevant to your "

            f"{high_risk_count} high-risk adult patients — "

            f"{trial_n:,}-patient trial showed 3-month fluoride "

            f"recall cuts caries recurrence 38% better than "

            f"6-month. Worth a look (2-min abstract). "

            f"Want me to pull it + draft a patient-ed WhatsApp "

            f"you can share? — {source}"

        )



        return build_action(



            trigger=trigger,



            merchant=merchant,



            customer=customer,



            body=body,



            template_name=(

                "vera_research_digest_v1"

            ),



            template_params=[

                f"Dr. {first_name}",



                (

                    f"{source} landed. One item relevant "

                    f"to your high-risk adult patients — "

                    f"{trial_n:,}-patient trial showed "

                    f"3-month fluoride recall cuts caries "

                    f"recurrence 38% better than 6-month"

                ),



                (

                    "Worth a look (2-min abstract). "

                    "Want me to pull it + draft a "

                    "patient-ed WhatsApp you can share?"

                )

            ],



            cta="open_ended",



            rationale=(

                "Selected the external research digest because "

                "its patient segment directly matches the "

                "merchant's high-risk adult cohort. The message "

                "uses the supplied trial size, measured effect "

                "and source, followed by a low-friction CTA."

            )

        )



    # --------------------------------------------------------

    # GENERIC RESEARCH FALLBACK

    # --------------------------------------------------------



    title = item.get(

        "title",

        "New research"

    )



    body = (

        f"{merchant_salutation(merchant, category)}, new research worth a look: "

        f"{title}. {summary} "

        f"Want me to pull the key takeaway and draft "

        f"a patient-facing message? — {source}"

    )



    return build_action(



        trigger=trigger,



        merchant=merchant,



        customer=customer,



        body=body,



        template_name=(

            "vera_research_digest_v1"

        ),



        template_params=[],



        cta="open_ended",



        rationale=(

            "Selected a relevant research digest and used "

            "only information supplied by the category context."

        )

    )





# ============================================================

# 8. REGULATION CHANGE

# ============================================================



def compose_regulation_change(

    trigger,

    merchant,

    category,

    customer=None

):



    payload = trigger.get(

        "payload",

        {}

    )



    item_id = (

        payload.get("top_item_id")

        or payload.get("item_id")

    )



    item = get_digest_item(

        category,

        item_id

    )



    if not item:



        return None



    title = item.get(

        "title",

        "Regulatory update"

    )



    summary = item.get(

        "summary",

        ""

    )



    source = item.get(

        "source",

        ""

    )



    deadline = payload.get(

        "deadline_iso"

    )



    first_name = merchant_first_name(

        merchant

    )



    deadline_text = ""



    if deadline:



        deadline_text = (

            f" Effective deadline: {deadline}."

        )



    body = (

        f"{merchant_salutation(merchant, category)}, regulatory update worth "

        f"flagging: {title}. "

        f"{summary}{deadline_text} "

        f"Want me to turn this into a simple "

        f"compliance checklist? — {source}"

    )



    return build_action(



        trigger=trigger,



        merchant=merchant,



        customer=customer,



        body=body,



        template_name=(

            "vera_regulation_update_v1"

        ),



        template_params=[],



        cta="open_ended",



        rationale=(

            "Selected a time-sensitive regulatory change "

            "and included the supplied deadline and source."

        )

    )





# ============================================================

# 9. PERFORMANCE DIP

# ============================================================



def compose_performance_dip(trigger, merchant, category, customer=None):
    payload = trigger.get("payload", {}) or {}
    metric = payload_value(payload, "metric")
    delta_pct = payload_value(payload, "delta_pct", "delta")
    window = payload_value(payload, "window") or "recent"
    baseline = payload_value(payload, "vs_baseline", "baseline")
    who = merchant_salutation(merchant, category)
    pct = percent_change(delta_pct)
    direction = "down" if isinstance(delta_pct, (int, float)) and delta_pct < 0 else "up"

    if metric and pct is not None:
        body = f"{who}, your {metric} is {pct:.0f}% {direction} over the {window} window."
        if baseline is not None:
            body += f" The supplied baseline is {baseline}."
        perf = merchant.get("performance", {}) or {}
        if metric == "calls" and perf.get("views") is not None:
            body += f" Your listing still has {human_number(perf['views'])} views in the 30-day window."
        elif metric == "views" and perf.get("calls") is not None:
            body += f" That listing has also generated {human_number(perf['calls'])} calls in the 30-day window."
        body += " Want me to identify the most likely driver and suggest one change?"
    else:
        fact = trigger_fact(payload)
        if fact is not None:
            body = f"{who}, there’s a {trigger.get('kind', 'business')} signal worth checking: {fact}. Want me to connect it to your current listing and suggest one next step?"
        else:
            body = f"{who}, I found a recent business signal worth checking. Want me to connect it to your current listing and suggest one next step?"

    return build_action(trigger=trigger, merchant=merchant, customer=customer,
                        body=body, template_name="vera_performance_check_v2",
                        template_params=[], cta="open_ended",
                        rationale="Prioritizes the supplied performance change and adds only directly available merchant context.")


# 10. RENEWAL

# ============================================================



def compose_renewal(trigger, merchant, category, customer=None):
    subscription = merchant.get("subscription", {}) or {}
    plan = subscription.get("plan", "current")
    days_remaining = subscription.get("days_remaining")
    who = merchant_salutation(merchant, category)
    offer = best_offer_label(merchant)

    if days_remaining is not None:
        body = f"{who}, your Vera {plan} subscription has {days_remaining} days remaining. "
        if offer:
            body += f"Your current active offer is {offer}. "
        body += "Before renewal, want me to review the current performance and flag one thing worth changing?"
    else:
        body = f"{who}, your Vera {plan} subscription is coming up for renewal. Want me to review the current performance before you decide what to do next?"

    return build_action(trigger=trigger, merchant=merchant, customer=customer,
                        body=body, template_name="vera_subscription_renewal_v2",
                        template_params=[], cta="open_ended",
                        rationale="Uses supplied renewal timing and active offer when available.")


# 11. CUSTOMER RECALL

# ============================================================



def compose_customer_recall(trigger, merchant, category, customer):
    payload = trigger.get("payload", {}) or {}
    kind = trigger.get("kind", "recall_due")
    customer_name = customer.get("first_name") or customer.get("name") or "there"
    slots = payload_value(payload, "available_slots", "slots") or []
    slot_labels = []
    for slot in slots[:3]:
        if isinstance(slot, dict):
            label = slot.get("label") or slot.get("time") or slot.get("start")
            if label: slot_labels.append(str(label))
        else:
            slot_labels.append(str(slot))
    service = payload_value(payload, "service", "treatment", "appointment_type", "trial")
    merchant_label = merchant_name(merchant)

    if kind == "appointment_tomorrow":
        body = f"Hi {customer_name}, this is {merchant_label}. Your appointment is tomorrow"
        if service: body += f" for {service}"
        body += "."
        if slot_labels: body += f" Available timing: {', '.join(slot_labels)}."
        body += " Please reply with the timing that works for you."
    elif kind == "trial_followup":
        body = f"Hi {customer_name}, this is {merchant_label}. "
        body += f"How did your {service} trial go? " if service else "How did your trial go? "
        body += "If you'd like, I can help with the next step."
    elif kind in {"customer_lapsed_soft", "customer_lapsed_hard"}:
        body = f"Hi {customer_name}, this is {merchant_label}. We haven't seen you recently. Would you like me to help you find a convenient time to come back?"
    elif kind == "chronic_refill_due":
        body = f"Hi {customer_name}, this is {merchant_label}. Your refill is due based on the supplied reminder. "
        body += f"Would one of these times work: {', '.join(slot_labels)}?" if slot_labels else "Would you like us to help arrange the next step?"
    else:
        body = f"Hi {customer_name}, this is {merchant_label}. Your follow-up is due."
        if service: body += f" This is regarding {service}."
        if slot_labels: body += f" We have {', '.join(slot_labels)} available."
        body += " Which works for you?"

    return build_action(trigger=trigger, merchant=merchant, customer=customer,
                        body=body, template_name="vera_customer_recall_v2",
                        template_params=slot_labels,
                        send_as="merchant_on_behalf",
                        cta="multi_choice_slot" if slot_labels else "open_ended",
                        rationale="Uses trigger-specific customer copy and only supplied service/slot context.")


# 12. GENERIC TRIGGER

# ============================================================



def compose_generic(trigger, merchant, category, customer=None):
    kind = trigger.get("kind", "signal")
    payload = trigger.get("payload", {}) or {}
    who = merchant_salutation(merchant, category)

    if kind in {"seasonal_event","category_seasonal","festival_upcoming","seasonal"}:
        event = payload_value(payload, "event","title","occasion","festival")
        date = payload_value(payload, "date","date_iso","event_date")
        offer = best_offer_label(merchant)
        body = f"{who}, "
        if event:
            body += f"{event}"
            if date: body += f" is coming up on {date}"
            body += ". "
        else:
            body += "there is a relevant seasonal opportunity coming up. "
        if offer:
            body += f"You already have {offer} active, so this could be a timely moment to refresh how it is presented. "
        else:
            body += f"This is a good moment to connect the event to {category_action_phrase(category)}. "
        body += "Want me to suggest one concrete campaign angle?"
    elif kind in {"review_theme","review_insight","reviews_signal"}:
        theme = payload_value(payload,"theme","title","reason","message")
        body = f"{who}, "
        body += f"your recent review signal is around “{theme}”. " if theme else "there is a review theme worth turning into an action. "
        body += "Want me to turn that customer feedback into one listing or offer change?"
    elif kind in {"milestone_reached","milestone"}:
        milestone = payload_value(payload,"milestone","title","message","count","value")
        body = f"{who}, you’ve reached {milestone if milestone is not None else 'a new business milestone'}. Want me to suggest one way to use the momentum?"
    elif kind in {"supply_alert","inventory_alert","stock_alert"}:
        item = payload_value(payload,"item","product","title","message")
        body = f"{who}, "
        body += f"there’s a supply alert for {item}. " if item else "there’s a supply alert that needs attention. "
        body += "Want me to help turn the alert into a concrete next step?"
    elif kind in {"gbp_unverified","listing_unverified","profile_unverified"}:
        body = f"{who}, your business profile has an unverified listing signal. Want me to walk through the verification step?"
    elif kind in {"active_planning_intent","planning_intent"}:
        intent = payload_value(payload,"intent","reason","message","title")
        body = f"{who}, "
        body += f"you have an active planning signal around {intent}. " if intent else "there’s an active planning signal worth acting on. "
        body += "Want me to turn it into one concrete next step?"
    elif kind in {"curiosity","merchant_curiosity","question"}:
        question = payload_value(payload,"question","message","title","reason")
        body = f"{who}, "
        body += f"you flagged: “{question}” " if question else "you flagged something worth exploring. "
        body += "Want me to pull the relevant context and give you the short answer?"
    else:
        fact = trigger_fact(payload)
        if fact is not None:
            body = f"{who}, there’s a {kind.replace('_',' ')} signal worth acting on: {fact}. Want me to connect it to your current listing and suggest one next step?"
        else:
            fact = merchant_context_fact(merchant)
            body = f"{who}, I found a {kind.replace('_',' ')} signal for your business. Given {fact}, want me to suggest one concrete next step?" if fact else f"{who}, I found a {kind.replace('_',' ')} signal worth checking. Want me to suggest one concrete next step?"

    return build_action(trigger=trigger, merchant=merchant, customer=customer,
                        body=body, template_name=f"vera_{kind}_v2",
                        template_params=[], cta="open_ended",
                        rationale="Uses trigger-specific language and supplied payload/merchant facts without inventing data.")


# 13. MAIN DECISION ENGINE

# ============================================================



def compose(

    trigger,

    merchant,

    category,

    customer=None

):



    # Safety checks

    if not trigger:

        return None



    if not merchant:

        return None



    if not category:

        return None



    kind = trigger.get(

        "kind",

        ""

    )



    scope = trigger.get(

        "scope"

    )



    # --------------------------------------------------------

    # CUSTOMER TRIGGERS

    # --------------------------------------------------------



    if (

        scope == "customer"

        and customer

    ):



        if kind in {

            "recall_due",

            "appointment_tomorrow",

            "trial_followup",

            "customer_lapsed_soft",

            "chronic_refill_due"

        }:



            return compose_customer_recall(

                trigger,

                merchant,

                category,

                customer

            )



    # --------------------------------------------------------

    # RESEARCH

    # --------------------------------------------------------



    if kind == "research_digest":



        return compose_research_digest(

            trigger,

            merchant,

            category,

            customer

        )



    # --------------------------------------------------------

    # REGULATION

    # --------------------------------------------------------



    if kind == "regulation_change":



        return compose_regulation_change(

            trigger,

            merchant,

            category,

            customer

        )



    # --------------------------------------------------------

    # PERFORMANCE

    # --------------------------------------------------------



    if kind in {

        "perf_dip",

        "seasonal_acquisition_dip",

        "ctr_below_peer_median"

    }:



        return compose_performance_dip(

            trigger,

            merchant,

            category,

            customer

        )



    # --------------------------------------------------------

    # RENEWAL

    # --------------------------------------------------------



    if kind in {

        "renewal_due",

        "subscription_renewal"

    }:



        return compose_renewal(

            trigger,

            merchant,

            category,

            customer

        )



    # --------------------------------------------------------

    # GENERIC FALLBACK

    # --------------------------------------------------------



    return compose_generic(

        trigger,

        merchant,

        category,

        customer

    )





# ============================================================

# 14. LOCAL TEST

# ============================================================



if __name__ == "__main__":



    print()

    print("=" * 70)

    print("VERA AI BOT - LOCAL TEST")

    print("=" * 70)



    print()

    print("Loaded contexts:")



    print(

        f"Categories : {len(CATEGORIES)}"

    )



    print(

        f"Merchants  : {len(MERCHANTS)}"

    )



    print(

        f"Customers  : {len(CUSTOMERS)}"

    )



    print(

        f"Triggers   : {len(TRIGGERS)}"

    )



    print()

    print("-" * 70)

    print(

        "Testing trg_001_research_digest_dentists"

    )

    print("-" * 70)



    trigger = get_trigger(

        "trg_001_research_digest_dentists"

    )



    merchant = get_merchant(

        "m_001_drmeera_dentist_delhi"

    )



    category = get_category(

        "dentists"

    )



    print()

    print(

        "Trigger found :",

        bool(trigger)

    )



    print(

        "Merchant found:",

        bool(merchant)

    )



    print(

        "Category found:",

        bool(category)

    )



    result = compose(

        trigger=trigger,

        merchant=merchant,

        category=category

    )



    print()

    print("-" * 70)

    print("BOT RESPONSE")

    print("-" * 70)



    print()



    print(

        json.dumps(

            result,

            indent=2,

            ensure_ascii=False

        )

    )



    print()

    print("=" * 70)

    print("TEST COMPLETE")

    print("=" * 70)

    
# ============================================================
# VERA AI — SCORING BOOST PATCH
# Append this block to the END of bot_logic.py
# ============================================================

def _safe_percent(value):
    if value is None:
        return None
    try:
        pct = float(value) * 100 if abs(float(value)) <= 1 else float(value)
        return f"{pct:.0f}%"
    except Exception:
        return str(value)


def _offer_text(merchant):
    offer = get_best_offer(merchant)
    if not offer:
        return None
    title = offer.get("title") or offer.get("name")
    price = offer.get("price")
    if title and price is not None:
        return f"{title} @ ₹{price}"
    return title


def _specialized_action(trigger, merchant, body, template_name, rationale,
                        customer=None, cta="open_ended"):
    return build_action(
        trigger=trigger,
        merchant=merchant,
        customer=customer,
        body=body,
        template_name=template_name,
        template_params=[],
        cta=cta,
        rationale=rationale
    )


# ------------------------------------------------------------
# STRONGER CUSTOMER COMPOSER
# ------------------------------------------------------------

def compose_customer_recall(trigger, merchant, category, customer):
    payload = trigger.get("payload") or {}
    customer_name = (
        customer.get("first_name")
        or customer.get("name")
        or "there"
    )

    kind = trigger.get("kind", "")
    slots = payload.get("available_slots") or payload.get("next_session_options") or []

    labels = []
    for slot in slots[:3]:
        if isinstance(slot, dict):
            label = slot.get("label") or slot.get("display")
            if label:
                labels.append(str(label))
        elif slot:
            labels.append(str(slot))

    offer = _offer_text(merchant)

    if kind in {"customer_lapsed_soft", "customer_lapsed_hard"}:
        days = payload.get("days_since_last_visit")
        focus = payload.get("previous_focus")
        if labels:
            slot_text = " or ".join(labels[:2])
        else:
            slot_text = None

        detail = []
        if days is not None:
            detail.append(f"it's been {days} days since your last visit")
        if focus:
            detail.append(f"you were previously working on {focus}")

        body = f"Hi {customer_name}, {merchant_name(merchant)} here. "
        body += " — ".join(detail) if detail else "we'd love to have you back"
        body += ". "
        if offer:
            body += f"We currently have {offer}. "
        if slot_text:
            body += f"I can hold {slot_text} if either works for you."
        else:
            body += "Want me to help find a convenient time?"

        return _specialized_action(
            trigger, merchant, body, "vera_customer_winback_v2",
            "Uses the lapse duration, prior customer intent and actual merchant offer/slots when supplied, with a low-friction return CTA.",
            customer=customer,
            cta="open_ended"
        )

    if kind == "trial_followup":
        trial_date = payload.get("trial_date")
        if labels:
            body = (
                f"Hi {customer_name}, {merchant_name(merchant)} here. "
                f"Following up on your trial"
                f"{' from ' + str(trial_date) if trial_date else ''}. "
                f"Next available option: {labels[0]}"
                f"{' or ' + labels[1] if len(labels) > 1 else ''}. "
                "Would you like me to reserve one?"
            )
        else:
            body = (
                f"Hi {customer_name}, {merchant_name(merchant)} here. "
                "Following up on your recent trial. "
                "Would you like me to help arrange your next session?"
            )

        return _specialized_action(
            trigger, merchant, body, "vera_trial_followup_v2",
            "Continues the trial journey using the supplied trial date and next-session options rather than sending a generic reminder.",
            customer=customer,
            cta="open_ended"
        )

    if kind == "chronic_refill_due":
        molecules = payload.get("molecule_list") or []
        stock_out = payload.get("stock_runs_out_iso")
        med_text = ", ".join(str(x) for x in molecules[:3])
        body = (
            f"Hi {customer_name}, {merchant_name(merchant)} here. "
            f"Your refill reminder is due"
            f"{' before ' + str(stock_out) if stock_out else ''}"
            f"{': ' + med_text if med_text else ''}. "
            "Would you like us to check availability and help arrange the refill?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_chronic_refill_v2",
            "Uses only the supplied refill timing and medicine list and asks the customer to confirm availability rather than making a medical recommendation.",
            customer=customer,
            cta="open_ended"
        )

    # Existing slot-based recall behavior, but more concrete.
    slot_text = " or ".join(labels[:2]) if labels else None
    body = f"Hi {customer_name}, {merchant_name(merchant)} here. "
    body += "Your follow-up is due. "
    if offer:
        body += f"We currently have {offer}. "
    if slot_text:
        body += f"Available times: {slot_text}. Which works for you?"
    else:
        body += "Would you like me to help find a convenient time?"

    return _specialized_action(
        trigger, merchant, body, "vera_customer_recall_v2",
        "Uses the customer-specific trigger and actual merchant offer/availability when supplied.",
        customer=customer,
        cta="open_ended"
    )


# ------------------------------------------------------------
# STRONGER GENERIC/EDGE-TRIGGER COMPOSER
# This overrides the old generic fallback without changing
# the existing strong research/regulation/performance/renewal
# composers.
# ------------------------------------------------------------

def compose_generic(trigger, merchant, category, customer=None):
    kind = trigger.get("kind", "")
    payload = trigger.get("payload") or {}
    name = merchant_name(merchant)
    first = merchant_first_name(merchant)
    category_name = category.get("slug", "your category")
    offer = _offer_text(merchant)

    # REVIEW THEME
    if kind == "review_theme_emerged":
        theme = payload.get("theme") or payload.get("topic") or "a recurring issue"
        occurrences = payload.get("occurrences_30d")
        trend = payload.get("trend")
        quote = payload.get("common_quote")

        count_text = f"{occurrences} reviews in 30 days" if occurrences is not None else "multiple recent reviews"
        trend_text = f", and the trend is {trend}" if trend else ""

        body = (
            f"{first}, {count_text} mention {theme}{trend_text}. "
            f"That is specific enough to act on rather than treat as noise."
        )
        if quote:
            body += f' One customer wording was: "{quote}".'
        body += " Want me to turn this into one concrete fix + a reply template?"

        return _specialized_action(
            trigger, merchant, body, "vera_review_theme_v2",
            "Turns the review pattern into an actionable merchant response using the supplied occurrence count, trend and customer wording."
        )

    # MILESTONE
    if kind == "milestone_reached":
        metric = payload.get("metric") or "milestone"
        current = payload.get("value_now")
        target = payload.get("milestone_value")

        if current is not None and target is not None:
            body = (
                f"{first}, you're at {current} {metric.replace('_', ' ')} "
                f"with {target - current} to go to {target}. "
                "You're close enough that the next step is worth planning now. "
                "Want me to draft a simple push to help reach it?"
            )
        elif target is not None:
            body = (
                f"{first}, you're approaching the {target} {metric.replace('_', ' ')} milestone. "
                "Want me to draft one concrete action to help get there?"
            )
        else:
            body = (
                f"{first}, you just hit a {metric.replace('_', ' ')} milestone. "
                "Want me to turn it into a simple customer-facing update?"
            )

        return _specialized_action(
            trigger, merchant, body, "vera_milestone_v2",
            "Uses the supplied milestone metric and values to create a concrete next action."
        )

    # ACTIVE PLANNING INTENT — give the merchant an artifact immediately.
    if kind == "active_planning_intent":
        topic = payload.get("intent_topic") or payload.get("topic") or "the idea"
        last_message = payload.get("merchant_last_message")

        body = (
            f"{first}, since you're already planning {topic.replace('_', ' ')}, "
            "here's the quickest next step: let's turn it into a first draft you can edit."
        )
        if offer:
            body += f" I can anchor it around your current {offer} where relevant."
        if last_message:
            body += f' You asked: "{last_message}"'
        body += " Want me to draft the actual customer-facing version now?"

        return _specialized_action(
            trigger, merchant, body, "vera_active_planning_v2",
            "Recognizes an active planning intent and moves directly to an artifact instead of restarting qualification."
        )

    # SEASONAL PERFORMANCE DIP
    if kind in {"seasonal_perf_dip", "seasonal_acquisition_dip"}:
        metric = payload.get("metric") or "performance"
        delta = _safe_percent(payload.get("delta_pct"))
        window = payload.get("window")
        expected = payload.get("is_expected_seasonal")
        note = payload.get("season_note")

        if expected:
            body = (
                f"{first}, {metric} is {delta + ' ' if delta else ''}down"
                f"{' over ' + str(window) if window else ''}, "
                "and this trigger flags the dip as seasonal rather than an anomaly."
            )
            if note:
                body += f" ({str(note).replace('_', ' ')})."
            body += (
                " I would avoid reacting with blanket spend and instead focus on "
                "a concrete retention or demand-capture action. Want me to draft one?"
            )
        else:
            body = (
                f"{first}, {metric} is showing a {delta + ' ' if delta else ''}change"
                f"{' over ' + str(window) if window else ''}. "
                "Want me to turn the signal into one concrete action to test?"
            )

        return _specialized_action(
            trigger, merchant, body, "vera_seasonal_perf_v2",
            "Reframes an explicitly seasonal performance signal instead of treating every dip as a generic performance problem."
        )

    # PERFORMANCE SPIKE
    if kind == "perf_spike":
        metric = payload.get("metric") or "performance"
        delta = _safe_percent(payload.get("delta_pct"))
        window = payload.get("window")

        body = (
            f"{first}, {metric} is up {delta or 'recently'}"
            f"{' over ' + str(window) if window else ''}. "
            "Before the signal fades, this is a good moment to capture what worked "
            "and turn it into a repeatable action. Want me to help isolate the likely driver?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_perf_spike_v2",
            "Uses the supplied positive performance movement and proposes a repeatable next action."
        )

    # DORMANT
    if kind == "dormant_with_vera":
        days = payload.get("days_since_last_message") or payload.get("days")
        body = (
            f"{first}, we haven't had a useful working conversation"
            f"{' in ' + str(days) + ' days' if days is not None else ' recently'}. "
            "Rather than send a generic nudge, I have one concrete item ready. "
            "Want to pick up from there?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_dormant_reengage_v2",
            "Uses the dormancy signal to reopen the working relationship without pretending there is a business problem."
        )

    # COMPETITOR
    if kind == "competitor_opened":
        distance = payload.get("distance_km")
        competitor = payload.get("competitor_name") or payload.get("name")
        category_text = payload.get("category") or category_name

        body = (
            f"{first}, a new {category_text} competitor"
            f"{' (' + str(competitor) + ')' if competitor else ''}"
            f"{' is about ' + str(distance) + ' km away' if distance is not None else ''}. "
            "The useful response is to protect your existing demand, not panic. "
            "Want me to suggest one concrete profile/offer move?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_competitor_v2",
            "Frames the competitor event around a concrete defensive action using only supplied competitor details."
        )

    # FESTIVAL / EVENT
    if kind in {"festival_upcoming", "festival"}:
        title = payload.get("festival") or payload.get("title") or "the upcoming event"
        days = payload.get("days_until") or payload.get("days")
        offer_text = f" Your active {offer} can be the anchor." if offer else ""

        body = (
            f"{first}, {title} is coming up"
            f"{' in ' + str(days) + ' days' if days is not None else ''}."
            f"{offer_text} "
            "Instead of a generic festival post, want me to draft one specific offer angle "
            "and the WhatsApp copy for it?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_festival_v2",
            "Connects the upcoming event to an actual merchant offer when available and proposes a concrete deliverable."
        )

    # SUPPLY ALERT / RECALL
    if kind in {"supply_alert", "product_recall"}:
        molecule = payload.get("molecule")
        batches = payload.get("affected_batches") or []
        manufacturer = payload.get("manufacturer")
        batch_text = ", ".join(str(x) for x in batches[:3])

        body = (
            f"{first}, a supply alert flags {molecule or 'a product'}"
            f"{' from ' + str(manufacturer) if manufacturer else ''}"
            f"{' affecting batches ' + batch_text if batch_text else ''}. "
            "Please verify the affected stock against your inventory before any further sale/dispensing. "
            "Want me to turn the supplied alert into a short internal checklist?"
        )

        return _specialized_action(
            trigger, merchant, body, "vera_supply_alert_v2",
            "Uses the supplied product, manufacturer and batch information and directs the merchant to verify affected stock without inventing regulatory instructions."
        )

    # CURIOUS ASK / LOW-FREQUENCY ENGAGEMENT
    if kind in {"curious_ask_due", "scheduled_recurring"}:
        signals = merchant.get("signals") or []
        signal_text = ", ".join(str(s) for s in signals[:2]) if signals else None

        body = (
            f"{first}, quick useful check for {name}: "
            "is there one thing you want more customers to do this week?"
        )
        if signal_text:
            body += f" I can use your current signal ({signal_text}) to suggest a concrete move."
        else:
            body += " If you tell me the priority, I'll turn it into a ready-to-use message."

        return _specialized_action(
            trigger, merchant, body, "vera_curiosity_v2",
            "Uses the recurring engagement trigger to start a useful business conversation rather than sending a generic promotion."
        )

    # Strong safe fallback — still grounded in the trigger.
    title = payload.get("title") or payload.get("topic") or payload.get("reason")
    if title:
        body = (
            f"{first}, {title}. "
            "This is the specific reason I'm reaching out now. "
            "Want me to turn it into one concrete next step?"
        )
    else:
        body = (
            f"{first}, I have a {kind.replace('_', ' ') or 'new'} signal for {name}. "
            "Want me to turn the supplied signal into one concrete next step?"
        )

    return _specialized_action(
        trigger, merchant, body,
        f"vera_{kind or 'context'}_v2",
        "Grounds the message in the trigger's supplied fact and offers one concrete next step without inventing data."
    )
