"""

First, a few callback functions are defined. Then, those functions are passed to

the Application and registered at their respective places.

Then, the bot is started and runs until we press Ctrl-C on the command line.


Usage:

Example of a bot-user conversation using ConversationHandler.

Send /start to initiate the conversation.

Press Ctrl-C on the command line or send a signal to the process to stop the

bot.

"""


import logging

import os
import traceback
from zoneinfo import ZoneInfo

import telegram
from telegram import __version__ as TG_VER, InlineKeyboardButton, InlineKeyboardMarkup
from booko import get_fields_filtered, get_home_coords
from datetime import date, datetime, timezone

try:

    from telegram import __version_info__

except ImportError:

    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]


if __version_info__ < (20, 0, 0, "alpha", 1):

    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)


# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)
from enum import Enum, auto


class TenantCallback(str, Enum):
    LOCATION = auto()
    ADDRESS = auto()
    TENANT_NAMES = auto()
    DEFAULT = auto()


# states
TENANT_FILTER, PRICE_FILTER, DISTANCE_FILTER, HOURS_FILTER, DATES_FILTER = map(
    chr, range(5)
)

# states for tenant_strategy
HANDLE_LOCATION, HANDLE_ADDRESS, HANDLE_NAMES, HANDLE_DEFAULT = map(chr, range(5, 9))
# Callback data
# LOCATION, ADDRESS, TENANT_NAMES, DEFAULT = range(9, 13)
# Shortcut for ConversationHandler.END

END = ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""

    # Get user that sent /start and log his name

    user = update.message.from_user

    logger.info("User %s started the conversation.", user.first_name)

    # Build InlineKeyboard where each button has a displayed text

    # and a string as callback_data

    # The keyboard is a list of button rows, where each row is in turn

    # a list (hence `[[...]]`).

    keyboard = [
        [
            InlineKeyboardButton("Address", callback_data=TenantCallback.ADDRESS),
            InlineKeyboardButton("Location", callback_data=TenantCallback.LOCATION),
            InlineKeyboardButton(
                "Field Names", callback_data=TenantCallback.TENANT_NAMES
            ),
            InlineKeyboardButton("Milan", callback_data=TenantCallback.DEFAULT),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message with text and appended InlineKeyboard

    await update.message.reply_text(
        "How do you want fields to be searched?", reply_markup=reply_markup
    )

    # Tell ConversationHandler that we're in state `FIRST` now

    return TENANT_FILTER


async def prompt_distance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Stores the info about the user and ends the conversation."""
    message = update.message or update.callback_query.message
    reply_keyboard = [["1", "2", "5", "10", "15", "20"]]
    await message.reply_text(
        f"Now select a distance for filtering",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Max distance?",
        ),
    )

    return DISTANCE_FILTER


async def tenant_filter_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """Show new choice of buttons"""

    query = update.callback_query
    choice = TenantCallback(query.data)
    await query.answer()
    match choice:
        case TenantCallback.ADDRESS:
            await query.edit_message_text(
                text="ok, send me the address",
            )

            return HANDLE_ADDRESS
        case TenantCallback.LOCATION:
            await query.edit_message_text(
                text="ok, send me the location",
            )

            return HANDLE_LOCATION
        case TenantCallback.TENANT_NAMES:
            await query.edit_message_text(
                text="ok, send me the field names (only one keyword per field)",
            )

            return HANDLE_NAMES
        case TenantCallback.DEFAULT:
            await query.edit_message_text(
                text="Will default to Milan",
            )

            return await prompt_distance(update, context)
        case _:
            await query.edit_message_text(
                text="unrecognized choice",
            )
            print("unrecognized tenant filter")
            return cancel
    # ReplyKeyboardMarkup(
    #
    #     reply_keyboard, one_time_keyboard=True, input_field_placeholder="Boy or Girl?"
    #
    # ),


async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""

    user = update.message.from_user
    address = update.message.text
    coords = get_home_coords(address)
    context.user_data["coords"] = coords
    ### do something with address

    return await prompt_distance(update, context)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""

    ### do something with address
    user = update.message.from_user

    user_location = update.message.location
    coords = user_location.latitude, user_location.longitude
    context.user_data["coords"] = coords

    return await prompt_distance(update, context)


async def handle_distance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""

    user = update.message.from_user
    distance = update.message.text
    context.user_data["distance"] = int(distance)
    reply_keyboard = [["10", "15", "30"]]
    await update.message.reply_text(
        f"Great, will max out at {distance} km- Now select a price for filtering",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Max price?",
        ),
    )

    return PRICE_FILTER


async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""

    user = update.message.from_user
    price = update.message.text
    context.user_data["max_price"] = int(price)
    reply_keyboard = [["10:00", "15:00", "18:00"]]
    await update.message.reply_text(
        f"Great, will show results at max {price} euro- Now select a start hour for filtering",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Max hour?",
        ),
    )

    return HOURS_FILTER


async def handle_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""
    from datetime import datetime, timedelta

    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    user = update.message.from_user
    hour = update.message.text
    context.user_data["min_hour"] = hour.split(":")[0]
    reply_keyboard = [[today.strftime("%d-%m"), tomorrow.strftime("%d-%m")]]
    await update.message.reply_text(
        f"Great, will show results at max {hour}\nNow select dates for filtering",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Date?",
        ),
    )

    return DATES_FILTER


def format_results(found_fields: dict[str, dict]):
    result_str = ""
    localtz = ZoneInfo("Europe/Rome")

    for date, tenants in found_fields.items():
        result_str += f"Found fields for date: {date}\n"
        for tenant in tenants:
            result_str += f"\n<b>{tenant['tenant_name']}</b>\n\n"

            for field in tenant["fields"]:
                result_str += f"\t{field['name']} - {field['properties']['resource_type']}\n"
                for slot in field["slots"]:
                    start_h = datetime.strptime(slot["start_time"], "%H:%M:%S")
                    start_h = datetime.combine(
                        date, start_h.time(), tzinfo=timezone.utc
                    )
                    start_h = start_h.astimezone(localtz)
                    result_str += f"\t\t\t@ {start_h.strftime('%H:%M')} {slot['duration']} mins {slot['price'].replace('EUR', '€')}\n"

        result_str += "=======================================\n"
    return result_str


async def handle_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:

    """Stores the selected gender and asks for a photo."""

    msg = await update.message.reply_text(
        f"Got ya. Let me fetch the results...",
        # reply_markup=ReplyKeyboardRemove(remove_keyboard = True)
    )
    await update.message.reply_chat_action(action=telegram.constants.ChatAction.TYPING)
    today = datetime.today()

    # user = update.message.from_user
    date_input = update.message.text
    date_input = date.fromisoformat(
        f"{today.year}-{date_input.split('-')[1]}-{date_input.split('-')[0]}"
    )
    user_data = context.user_data
    result = get_fields_filtered(
        user_data.get("coords", None),
        user_data.get("field_names", None),
        user_data["distance"],
        user_data["min_hour"],
        user_data["max_price"],
        [date_input],
    )
    result_str = format_results(result)
    if result_str != "":

        await msg.edit_text("Done")
        await update.message.reply_text(
            result_str,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=telegram.constants.ParseMode.HTML,
        )
    else:
        await msg.edit_text("Didn't find any field with selected filters")

    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Cancels and ends the conversation."""

    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:

    """Log the error and send a telegram message to notify the developer."""

    # Log the error before we do anything else, so we can see it even if something breaks.

    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a

    # list of strings rather than a single string, so we have to join them together.

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )

    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.

    # You might need to add some logic to deal with messages longer than the 4096 character limit.

    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    await update.message.reply_text(
        "Something went wrong. Please start again", reply_markup=ReplyKeyboardRemove()
    )
    return END


def main() -> None:

    """Run the bot."""

    # Create the Application and pass it your bot's token.
    mode = os.environ.get("MODE", "polling")
    token = os.environ.get("TOKEN")
    port = os.environ.get("PORT", "7880")
    expose_url = os.environ.get("EXPOSE_URL", "")
    application = Application.builder().token(token).build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("fields", start)],
        states={
            TENANT_FILTER: [
                CallbackQueryHandler(tenant_filter_choice),
            ],
            HANDLE_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address)
            ],
            HANDLE_LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
            ],
            DISTANCE_FILTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_distance)
            ],
            PRICE_FILTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)
            ],
            HOURS_FILTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hour)
            ],
            DATES_FILTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dates)
            ],
            # PHOTO: [
            #     MessageHandler(filters.PHOTO, photo),
            #     CommandHandler("skip", skip_photo),
            # ],
            # LOCATION: [
            #     MessageHandler(filters.LOCATION, location),
            #     CommandHandler("skip", skip_location),
            # ],
            # BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    # Run the bot until the user presses Ctrl-C
    if mode == "webhook":
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{expose_url}/{token}",
        )
    else:
        application.run_polling()


if __name__ == "__main__":

    main()
