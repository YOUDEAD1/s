from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from subscription_service import SubscriptionService
# تعديل: جعل استيراد AuthService اختيارياً
try:
    from auth_service import AuthService
    HAS_AUTH_SERVICE = True
except ImportError:
    HAS_AUTH_SERVICE = False
from group_service import GroupService
from posting_service import PostingService
try:
    from response_service import ResponseService
    HAS_RESPONSE_SERVICE = True
except ImportError:
    HAS_RESPONSE_SERVICE = False
try:
    from referral_service import ReferralService
    HAS_REFERRAL_SERVICE = True
except ImportError:
    HAS_REFERRAL_SERVICE = False

class StartHelpHandlers:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.subscription_service = SubscriptionService()
        # تعديل: التحقق من وجود الخدمات قبل استخدامها
        if HAS_AUTH_SERVICE:
            self.auth_service = AuthService()
        else:
            self.auth_service = None
        self.group_service = GroupService()
        self.posting_service = PostingService()
        if HAS_RESPONSE_SERVICE:
            self.response_service = ResponseService()
        else:
            self.response_service = None
        if HAS_REFERRAL_SERVICE:
            self.referral_service = ReferralService()
        else:
            self.referral_service = None

        # Register handlers
        self.register_handlers()

    def register_handlers(self):
        # Register start and help commands
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))

        # Register callback queries - Fix: Use more specific pattern to avoid conflicts
        self.dispatcher.add_handler(CallbackQueryHandler(self.start_help_callback, pattern='^(start_|help_)'))

    async def start_command(self, update: Update, context: CallbackContext):
        """Handle the /start command with interactive buttons"""
        user = update.effective_user
        user_id = user.id

        # Get or create user in database
        db_user = self.subscription_service.get_user(user_id)
        if not db_user:
            db_user = self.subscription_service.create_user(
                user_id,
                user.username,
                user.first_name,
                user.last_name
            )

        # Check if admin
        is_admin = db_user and db_user.is_admin

        # Welcome message
        welcome_text = f"👋 مرحباً {user.first_name}!\n\n"

        if is_admin:
            welcome_text += "🔰 أنت مسجل كمشرف في النظام.\n\n"

        welcome_text += "🤖 أنا بوت احترافي للنشر التلقائي في مجموعات تيليجرام.\n\n"

        # Check subscription status
        has_subscription = db_user.has_active_subscription()

        # Create keyboard with options
        keyboard = []

        # Add referral button for all users (new feature)
        keyboard.append([
            InlineKeyboardButton("🔗 الإحالة", callback_data="start_referral")
        ])

        if has_subscription:
            if db_user.subscription_end:
                end_date = db_user.subscription_end.strftime('%Y-%m-%d')
                welcome_text += f"✅ لديك اشتراك نشط حتى: {end_date}\n\n"
            else:
                welcome_text += f"✅ لديك اشتراك نشط غير محدود المدة\n\n"

            # Check if user is logged in
            session_string = None
            if self.auth_service is not None:
                session_string = self.auth_service.get_user_session(user_id)
            if session_string:
                welcome_text += "✅ أنت مسجل الدخول بالفعل ويمكنك استخدام جميع ميزات البوت.\n\n"

                # Add main feature buttons
                keyboard.append([
                    InlineKeyboardButton("👥 المجموعات", callback_data="start_groups"),
                    InlineKeyboardButton("📝 النشر", callback_data="start_post")
                ])

                keyboard.append([
                    InlineKeyboardButton("🤖 الردود التلقائية", callback_data="start_responses")
                ])

                # Add account management buttons
                keyboard.append([
                    InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups"),
                    InlineKeyboardButton("📊 حالة النشر", callback_data="start_status")
                ])

                keyboard.append([
                    InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
                ])

                # Add admin button if user is admin
                if is_admin:
                    keyboard.append([
                        InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                    ])
            else:
                welcome_text += "⚠️ أنت لم تقم بتسجيل الدخول بعد.\n\n"

                # Add login buttons
                keyboard.append([
                    InlineKeyboardButton("🔑 تسجيل الدخول", callback_data="start_login"),
                    InlineKeyboardButton("🔐 إنشاء Session", callback_data="start_generate_session")
                ])

                keyboard.append([
                    InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
                ])

                # Add admin button if user is admin
                if is_admin:
                    keyboard.append([
                        InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                    ])
        else:
            welcome_text += "⚠️ ليس لديك اشتراك نشط.\n\n"

            # Create keyboard with subscription option
            keyboard.append([
                InlineKeyboardButton("🔔 طلب اشتراك", callback_data="start_subscription")
            ])

            keyboard.append([
                InlineKeyboardButton("📋 المساعدة", callback_data="start_help")
            ])

            # Add admin button if user is admin
            if is_admin:
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 لوحة المشرف", callback_data="start_admin")
                ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: CallbackContext):
        """Handle the /help command with interactive buttons"""
        user = update.effective_user
        user_id = user.id

        # Get user from database
        db_user = self.subscription_service.get_user(user_id)
        is_admin = db_user and db_user.is_admin
        has_subscription = db_user and db_user.has_active_subscription()

        help_text = "📋 قائمة الأوامر المتاحة:\n\n"

        # Create keyboard with help categories
        keyboard = [
            [InlineKeyboardButton("🔑 أوامر الحساب", callback_data="help_account")],
            [InlineKeyboardButton("👥 أوامر المجموعات", callback_data="help_groups")],
            [InlineKeyboardButton("📝 أوامر النشر", callback_data="help_posting")],
            [InlineKeyboardButton("🤖 أوامر الردود", callback_data="help_responses")],
            [InlineKeyboardButton("🔗 أوامر الإحالات", callback_data="help_referrals")]
        ]

        # Add admin button if user is admin
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("👨‍💼 أوامر المشرف", callback_data="help_admin")
            ])

        # Add back to start button
        keyboard.append([
            InlineKeyboardButton("🔙 العودة للبداية", callback_data="help_back_to_start")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=help_text,
            reply_markup=reply_markup
        )

    async def start_help_callback(self, update: Update, context: CallbackContext):
        """Handle start and help related callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        # Get user from database
        db_user = self.subscription_service.get_user(user_id)
        is_admin = db_user and db_user.is_admin
        has_subscription = db_user and db_user.has_active_subscription()

        # Handle start callbacks - تحسين: تنفيذ الإجراءات مباشرة بدلاً من طلب استخدام الأوامر
        if data == "start_subscription":
            # تنفيذ إجراء طلب الاشتراك مباشرة
            if hasattr(context.bot, 'subscription_handlers') and hasattr(context.bot.subscription_handlers, 'subscription_command'):
                await context.bot.subscription_handlers.subscription_command(update, context)
            else:
                # إذا لم يكن معالج الاشتراك متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="💳 *طلب اشتراك جديد*\n\nيرجى التواصل مع المشرف للحصول على اشتراك جديد.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_login":
            # تنفيذ إجراء تسجيل الدخول مباشرة
            if HAS_AUTH_SERVICE and hasattr(context.bot, 'auth_handlers') and hasattr(context.bot.auth_handlers, 'login_command'):
                await context.bot.auth_handlers.login_command(update, context)
            else:
                # إذا لم يكن معالج تسجيل الدخول متاحاً، بدء محادثة تسجيل الدخول
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🔑 *تسجيل الدخول*\n\nيرجى إرسال رقم الهاتف بتنسيق دولي (مثال: +966123456789).",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_generate_session":
            # تنفيذ إجراء إنشاء جلسة مباشرة
            if HAS_AUTH_SERVICE and hasattr(context.bot, 'auth_handlers') and hasattr(context.bot.auth_handlers, 'generate_session_command'):
                await context.bot.auth_handlers.generate_session_command(update, context)
            else:
                # إذا لم يكن معالج إنشاء الجلسة متاحاً، بدء محادثة إنشاء الجلسة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🔐 *إنشاء Session String*\n\nيرجى إرسال API ID الخاص بك.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_groups":
            # تنفيذ إجراء إدارة المجموعات مباشرة
            if hasattr(context.bot, 'group_handlers') and hasattr(context.bot.group_handlers, 'groups_command'):
                await context.bot.group_handlers.groups_command(update, context)
            else:
                # إذا لم يكن معالج المجموعات متاحاً، عرض قائمة المجموعات
                user_id = update.effective_user.id
                groups = self.group_service.get_user_groups(user_id)

                if not groups:
                    keyboard = [[InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups")],
                               [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="👥 *المجموعات*\n\nلم يتم العثور على مجموعات. يرجى تحديث المجموعات أولاً.",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    # إنشاء لوحة مفاتيح مع المجموعات
                    keyboard = []
                    for group in groups:
                        group_id = str(group.get('group_id'))
                        group_name = group.get('title', 'مجموعة بدون اسم')
                        is_blacklisted = group.get('blacklisted', False)
                        emoji = "🔴" if is_blacklisted else "🟢"
                        keyboard.append([InlineKeyboardButton(f"{emoji} {group_name}", callback_data=f"group:{group_id}")])

                    keyboard.append([InlineKeyboardButton("🔄 تحديث المجموعات", callback_data="start_refresh_groups")])
                    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="start_back")])

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="👥 *المجموعات*\n\nاختر مجموعة للتحكم بها:",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

        elif data == "start_post":
            # تنفيذ إجراء النشر مباشرة
            if hasattr(context.bot, 'posting_handlers') and hasattr(context.bot.posting_handlers, 'start_post'):
                # استخدام معالج النشر مباشرة
                # نحتاج إلى إنشاء رسالة وهمية لتمرير إلى معالج النشر
                class DummyMessage:
                    def __init__(self, chat_id, from_user):
                        self.chat_id = chat_id
                        self.from_user = from_user

                    async def reply_text(self, text, reply_markup=None, parse_mode=None):
                        # استبدال رسالة الاستعلام بدلاً من إرسال رسالة جديدة
                        await query.edit_message_text(
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )

                # إنشاء رسالة وهمية
                update.message = DummyMessage(
                    chat_id=update.effective_chat.id,
                    from_user=update.effective_user
                )

                # استدعاء معالج النشر
                await context.bot.posting_handlers.start_post(update, context)
            else:
                # إذا لم يكن معالج النشر متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="📝 *النشر في المجموعات*\n\nيرجى استخدام الأمر /post لبدء النشر في المجموعات.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_responses":
            # تنفيذ إجراء الردود التلقائية مباشرة
            if HAS_RESPONSE_SERVICE and hasattr(context.bot, 'response_handlers') and hasattr(context.bot.response_handlers, 'auto_response_command'):
                await context.bot.response_handlers.auto_response_command(update, context)
            else:
                # إذا لم يكن معالج الردود التلقائية متاحاً، عرض رسالة بديلة
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="🤖 *الردود التلقائية*\n\nيمكنك إعداد ردود تلقائية للرسائل الواردة.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_referral":
            # تنفيذ إجراء الإحالة مباشرة
            if HAS_REFERRAL_SERVICE and hasattr(context.bot, 'referral_handlers') and hasattr(context.bot.referral_handlers, 'referral_command'):
                await context.bot.referral_handlers.referral_command(update, context)
            else:
                # إذا لم يكن معالج الإحالة متاحاً، عرض رسالة بديلة
                user_id = update.effective_user.id
                referral_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=f"🔗 *رابط الإحالة الخاص بك*\n\n`{referral_link}`\n\nشارك هذا الرابط مع أصدقائك للحصول على مكافآت!",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        elif data == "start_refresh_groups":
            # تنفيذ إجراء تحديث المجموعات مباشرة
            if hasattr(context.bot, 'group_handlers') and hasattr(context.bot.group_handlers, 'refresh_groups_command'):
                await context.bot.group_handlers.refresh_groups_command(update, context)
            else:
                # إذا لم يكن معالج تحديث المجموعات متاحاً، استخدم خدمة المجموعات مباشرة
                user_id = update.effective_user.id

                # إرسال رسالة تحميل
                await query.edit_message_text(
                    text="⏳ جاري جلب المجموعات من تيليجرام..."
                )

                # جلب المجموعات
                success, result_message, groups = await self.group_service.fetch_user_groups(user_id)

                if success:
                    # إنشاء لوحة مفاتيح مع المجموعات
                    keyboard = []
                    for group in groups:
                        group_id = str(group.get('id'))
                        group_name = group.get('title', 'مجموعة بدون اسم')
                        keyboard.append([InlineKeyboardButton(f"🟢 {group_name}", callback_data=f"group:{group_id}")])

                    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="start_back")])

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text=f"✅ {result_message}\n\n👥 المجموعات المتاحة:",
                        reply_markup=reply_markup
                    )
                else:
                    # عرض رسالة الخطأ
                    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text=f"❌ {result_message}",
                        reply_markup=reply_markup
                    )

        elif data == "start_status":
            # تنفيذ إجراء التحقق من حالة النشر مباشرة
            if hasattr(context.bot, 'posting_handlers') and hasattr(context.bot.posting_handlers, 'check_status'):
                await context.bot.posting_handlers.check_status(update, context)
            else:
                # إذا لم يكن معالج حالة النشر متاحاً، استخدم خدمة النشر مباشرة
                user_id = update.effective_user.id
                status = self.posting_service.get_posting_status(user_id)

                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if status and status.get('is_active', False):
                    await query.edit_message_text(
                        text=f"📊 *حالة النشر*\n\n✅ النشر نشط حالياً\nتم نشر {status.get('posts_count', 0)} رسالة\nبدأ في: {status.get('start_time', 'غير معروف')}",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    await query.edit_message_text(
                        text="📊 *حالة النشر*\n\n❌ لا توجد عملية نشر نشطة حالياً.",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

        elif data == "start_admin":
            # تنفيذ إجراء لوحة المشرف مباشرة
            if hasattr(context.bot, 'admin_handlers') and hasattr(context.bot.admin_handlers, 'admin_command'):
                await context.bot.admin_handlers.admin_command(update, context)
            else:
                # إذا لم يكن معالج لوحة المشرف متاحاً، عرض قائمة أوامر المشرف
                keyboard = [
                    [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
                    [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="admin_broadcast")],
                    [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="👨‍💼 *لوحة المشرف*\n\nاختر إحدى الخيارات التالية:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        # إضافة معالج زر العودة
        elif data == "start_back":
            # العودة إلى قائمة البداية
            await self.start_command(update, context)

        elif data == "start_help":
            # Redirect to help command
            await self.help_command(update, context)

        # Handle help callbacks
        elif data == "help_account":
            # Show account commands
            message = "🔑 أوامر الحساب:\n\n"
            message += "🔹 /subscription - التحقق من حالة الاشتراك\n"
            message += "🔹 /login - تسجيل الدخول إلى حساب التيليجرام\n"
            message += "🔹 /logout - تسجيل الخروج من حساب التيليجرام\n"
            message += "🔹 /generate_session - توليد Session String جديد\n"
            message += "🔹 /api_info - معلومات حول كيفية الحصول على API ID و API Hash\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        elif data == "help_groups":
            # Show groups commands
            message = "👥 أوامر المجموعات:\n\n"
            message += "🔹 /groups - إدارة المجموعات\n"
            # تصحيح: توحيد أوامر تحديث المجموعات
            message += "🔹 /refresh - تحديث قائمة المجموعات\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        elif data == "help_posting":
            # Show posting commands
            message = "📝 أوامر النشر:\n\n"
            message += "🔹 /post - بدء عملية النشر في المجموعات\n"
            # تصحيح: تغيير الأمر من stop_posting إلى stop
            message += "🔹 /stop - إيقاف عملية النشر الحالية\n"
            message += "🔹 /status - التحقق من حالة النشر الحالية\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        elif data == "help_responses":
            # Show responses commands
            message = "🤖 أوامر الردود التلقائية:\n\n"
            message += "🔹 /auto_response - التحكم في الردود التلقائية\n"
            message += "🔹 /start_responses - تفعيل الردود التلقائية\n"
            message += "🔹 /stop_responses - إيقاف الردود التلقائية\n"
            message += "🔹 /customize_responses - تخصيص الردود التلقائية\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        elif data == "help_referrals":
            # Show referrals commands
            message = "🔗 أوامر الإحالات:\n\n"
            message += "🔹 /referral - الحصول على رابط الإحالة الخاص بك\n"
            message += "🔹 /my_referrals - عرض إحالاتك\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        elif data == "help_admin":
            # Show admin commands
            message = "👨‍💼 أوامر المشرف:\n\n"
            message += "🔹 /admin - لوحة تحكم المشرف\n"
            message += "🔹 /adduser USER_ID DAYS - إضافة اشتراك لمستخدم\n"
            message += "🔹 /removeuser USER_ID - إلغاء اشتراك مستخدم\n"
            message += "🔹 /checkuser USER_ID - التحقق من حالة اشتراك مستخدم\n"
            message += "🔹 /listusers - عرض قائمة المستخدمين مع اشتراكات نشطة\n"
            message += "🔹 /broadcast MESSAGE - إرسال رسالة جماعية لجميع المستخدمين\n"
            message += "🔹 /channel_subscription - إدارة الاشتراك الإجباري في القناة\n"
            message += "🔹 /get_updated_files - الحصول على جميع الملفات المحدثة\n"
            message += "🔹 /statistics  -  عرض احصائيات المستخدمين و نشاطهم في مجموعات\n"

            # Create back button
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="help_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )

        # Fix: Properly handle back button callbacks
        elif data == "help_back":
            # Go back to help main menu
            try:
                # Use the help_command method but with the callback query
                help_text = "📋 قائمة الأوامر المتاحة:\n\n"

                # Create keyboard with help categories
                keyboard = [
                    [InlineKeyboardButton("🔑 أوامر الحساب", callback_data="help_account")],
                    [InlineKeyboardButton("👥 أوامر المجموعات", callback_data="help_groups")],
                    [InlineKeyboardButton("📝 أوامر النشر", callback_data="help_posting")],
                    [InlineKeyboardButton("🤖 أوامر الردود", callback_data="help_responses")],
                    [InlineKeyboardButton("🔗 أوامر الإحالات", callback_data="help_referrals")]
                ]

                # Add admin button if user is admin
                if is_admin:
                    keyboard.append([
                        InlineKeyboardButton("👨‍💼 أوامر المشرف", callback_data="help_admin")
                    ])

                # Add back to start button
                keyboard.append([
                    InlineKeyboardButton("🔙 العودة للبداية", callback_data="help_back_to_start")
                ])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    text=help_text,
                    reply_markup=reply_markup
                )
            except Exception as e:
                # If there's an error, just send a new help message
                await self.help_command(update, context)

        elif data == "help_back_to_start":
            # Go back to start command
            await self.start_command(update, context)
