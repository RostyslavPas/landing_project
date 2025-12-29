const { useState } = React;

const ChevronLeft = () => (
    React.createElement('svg', {
        width: "24",
        height: "24",
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: "2"
    },
        React.createElement('polyline', { points: "15 18 9 12 15 6" })
    )
);

const ChevronRight = () => (
    React.createElement('svg', {
        width: "24",
        height: "24",
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: "2"
    },
        React.createElement('polyline', { points: "9 18 15 12 9 6" })
    )
);

const Heart = () => (
  React.createElement('img', {
    src: 'static/images/btn-heart-1.png',
    width: 42,
    height: 42,
    style: { flexShrink: 0 }
  })
);

const MonthlyScheduleCarousel = ({ initialSlide = null }) => {
    // Функція для визначення поточного місяця
    const getCurrentMonthIndex = () => {
        const currentMonth = new Date().getMonth(); // 0 = Січень, 11 = Грудень

        // Мапінг місяців до індексів слайдів
        const monthMapping = {
            11: 0, // Грудень
            0: 1,  // Січень
            1: 2,  // Лютий
            2: 0,  // Березень -> показуємо Грудень
            3: 0,  // Квітень -> показуємо Грудень
            4: 0,  // Травень -> показуємо Грудень
            5: 0,  // Червень -> показуємо Грудень
            6: 0,  // Липень -> показуємо Грудень
            7: 0,  // Серпень -> показуємо Грудень
            8: 0,  // Вересень -> показуємо Грудень
            9: 0,  // Жовтень -> показуємо Грудень
            10: 0  // Листопад -> показуємо Грудень
        };

        return monthMapping[currentMonth] || 0;
    };

    // Визначаємо початковий слайд автоматично по даті
    const getInitialSlide = () => {
        if (initialSlide !== null && initialSlide >= 0) {
            return initialSlide;
        }
        return getCurrentMonthIndex();
    };

    const [currentSlide, setCurrentSlide] = useState(getInitialSlide());

    const schedules = [
        {
            month: "ГРУДЕНЬ",
            monthNumber: 12,
            subtitle: "КОЖНОГО МІСЯЦЯ НОВА ТЕМА",
            title: "РОЗКЛАД НА ГРУДЕНЬ",
            tagline: "Підсумки року з турботою про себе",
            items: [
                "12 тренувань зі стрейчингу з поясненням кожної вправи",
                "4 психологічні сесії з практичними завданнями",
                "4 астрологічні прогнози на тиждень",
                "2 гороскопи на новолуння та повнолуння",
                "Готовий план харчування на тиждень",
                "Різдвяне меню: 12 корисних страв для святкового столу"
            ],
            bonus: {
                label: "БОНУСНЕ ВІДЕО ГРУДНЯ:",
                text: "Визначаємо свій Асцендент і розбираємо для кожного знака Зодіака"
            }
        },
        {
            month: "СІЧЕНЬ",
            monthNumber: 1,
            subtitle: "КОЖНОГО МІСЯЦЯ НОВА ТЕМА",
            title: "РОЗКЛАД НА СІЧЕНЬ",
            tagline: "Новий старт із мудрістю і вірою в себе",
            items: [
                "12 тренувань зі стрейчингу з поясненням кожної вправи",
                "4 психологічні сесії з практичними завданнями",
                "4 астрологічні прогнози на тиждень",
                "2 гороскопи на новолуння та повнолуння",
                "Готові плани харчування на тиждень"
            ],
            bonus: {
                label: "БОНУСНЕ ВІДЕО СІЧНЯ:",
                text: "Сонце у натальній карті: твоя життєва місія і внутрішнє світло"
            }
        },
        {
            month: "ЛЮТИЙ",
            monthNumber: 2,
            subtitle: "КОЖНОГО МІСЯЦЯ НОВА ТЕМА",
            title: "РОЗКЛАД НА ЛЮТИЙ",
            tagline: "Про любов до себе і до життя",
            items: [
                "12 тренувань зі стрейчингу з поясненням кожної вправи",
                "Психологічні практики та челенджі",
                "4 астрологічні прогнози на тиждень",
                "2 гороскопи на новолуння та повнолуння",
                "Готові плани харчування на тиждень"
            ],
            bonus: {
                label: "БОНУСНЕ ВІДЕО ЛЮТОГО:",
                text: "Місяць в натальній карті: про внутрішній світ, емоції, інстинкти та підсвідомість"
            }
        }
    ];

    const nextSlide = () => {
        setCurrentSlide((prev) => (prev + 1) % schedules.length);
    };

    const prevSlide = () => {
        setCurrentSlide((prev) => (prev - 1 + schedules.length) % schedules.length);
    };

    const goToSlide = (index) => {
        setCurrentSlide(index);
    };

    // Стилі для контейнера
    const containerStyle = {
        width: '100%',
        maxWidth: '448px',
        margin: '0 auto',
        padding: '10px 0'
    };

    // Стилі для обгортки слайдів
    const sliderWrapperStyle = {
        position: 'relative'
    };

    // Стилі дляoverflow контейнера
    const overflowContainerStyle = {
        overflow: 'hidden',
        borderRadius: '24px'
    };

    // Стилі для треку слайдів
    const slidesTrackStyle = {
        display: 'flex',
        transition: 'transform 500ms ease-out',
        transform: `translateX(-${currentSlide * 100}%)`
    };

    // Стилі для окремого слайду
    const slideStyle = {
        width: '100%',
        flexShrink: 0
    };

    // Стилі для картки
    const cardStyle = {
        background: '#fae6ed',
        borderRadius: '24px',
        padding: '20px',
        border: '2px solid #fbcfe8',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
    };

    // Стилі для subtitle
    const subtitleStyle = {
        fontSize: '12px',
        textAlign: 'center',
        color: '#b08a9a',
        letterSpacing: '0.12em',
        marginBottom: '8px',
        textTransform: 'uppercase'
    };

    // Стилі для title
    const titleStyle = {
        fontSize: '22px',
        fontWeight: 'bold',
        textAlign: 'center',
        textTransform: 'uppercase',
        margin: '0 0 5px'
    };

    // Стилі для tagline
    const taglineStyle = {
        fontSize: '14px',
        textAlign: 'center',
        color: '#be185d',
        fontWeight: '500',
        margin: '0 0 20px'
    };

    // Стилі для списку
    const listStyle = {
        listStyle: 'none',
        textAlign: 'left',
        padding: 0,
        margin: '0 0 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
    };

    // Стилі для елементу списку
    const listItemStyle = {
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        background: 'white',
        border: '1px dashed #fbcfe8',
        padding: '12px 16px',
        borderRadius: '50px'
    };

    // Стилі для тексту в списку
    const listItemTextStyle = {
        fontSize: '13px',
        lineHeight: '1.4',
        textAlign: 'left',
        flex: 1
    };

    // Стилі для бонусу
    const bonusContainerStyle = {
        textAlign: 'center',
        marginBottom: '20px'
    };

    const bonusLabelStyle = {
        fontSize: '18px',
        fontWeight: '600',
        color: '#be185d',
        letterSpacing: '0.05em',
        marginBottom: '4px'
    };

    const bonusTextStyle = {
        fontSize: '14px',
        color: '#9f1239',
        marginBottom: '30px'
    };

    // Стилі для кнопок навігації
    const navButtonStyle = {
        position: 'absolute',
        top: '50%',
        transform: 'translateY(-50%)',
        background: 'white',
        borderRadius: '50%',
        padding: '8px',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        border: 'none',
        cursor: 'pointer',
        transition: 'background-color 200ms',
        zIndex: 10
    };

    const prevButtonStyle = {
        ...navButtonStyle,
        left: '-16px'
    };

    const nextButtonStyle = {
        ...navButtonStyle,
        right: '-16px'
    };

    // Стилі для dots
    const dotsContainerStyle = {
        display: 'flex',
        justifyContent: 'center',
        gap: '8px',
        marginTop: '24px'
    };

    const dotStyle = (isActive) => ({
        height: '8px',
        width: isActive ? '32px' : '8px',
        borderRadius: '9999px',
        background: isActive ? '#be185d' : '#fbcfe8',
        border: 'none',
        cursor: 'pointer',
        transition: 'all 200ms',
        padding: 0
    });

    return React.createElement('div', { style: containerStyle },
        React.createElement('div', { style: sliderWrapperStyle },
            React.createElement('div', { style: overflowContainerStyle },
                React.createElement('div', { style: slidesTrackStyle },
                    schedules.map((schedule, index) =>
                        React.createElement('div', { key: index, style: slideStyle },
                            React.createElement('div', { style: cardStyle },
                                React.createElement('p', { style: subtitleStyle }, schedule.subtitle),
                                React.createElement('h2', { style: titleStyle }, schedule.title),
                                React.createElement('p', { style: taglineStyle }, schedule.tagline),
                                React.createElement('ul', { style: listStyle },
                                    schedule.items.map((item, idx) =>
                                        React.createElement('li', {
                                            key: idx,
                                            style: listItemStyle
                                        },
                                            React.createElement(Heart),
                                            React.createElement('span', { style: listItemTextStyle }, item)
                                        )
                                    )
                                ),
                                React.createElement('div', { style: bonusContainerStyle },
                                    React.createElement('p', { style: bonusLabelStyle }, schedule.bonus.label),
                                    React.createElement('p', { style: bonusTextStyle }, schedule.bonus.text)
                                ),
                                React.createElement('a', {
                                    href: "#form",
                                    className: "cta-button cta-button--primary month-schedule-btn",
                                    style: { display: 'block', textAlign: 'center', textDecoration: 'none' }
                                },
                                    React.createElement('span', {}, "Купити підписку на місяць")
                                )
                            )
                        )
                    )
                )
            ),
            React.createElement('button', {
                onClick: prevSlide,
                style: prevButtonStyle,
                onMouseEnter: (e) => e.target.style.background = '#fdf2f8',
                onMouseLeave: (e) => e.target.style.background = 'white'
            }, React.createElement(ChevronLeft)),
            React.createElement('button', {
                onClick: nextSlide,
                style: nextButtonStyle,
                onMouseEnter: (e) => e.target.style.background = '#fdf2f8',
                onMouseLeave: (e) => e.target.style.background = 'white'
            }, React.createElement(ChevronRight))
        ),
        React.createElement('div', { style: dotsContainerStyle },
            schedules.map((_, index) =>
                React.createElement('button', {
                    key: index,
                    onClick: () => goToSlide(index),
                    style: dotStyle(index === currentSlide),
                    onMouseEnter: (e) => {
                        if (index !== currentSlide) {
                            e.target.style.background = '#f9a8d4';
                        }
                    },
                    onMouseLeave: (e) => {
                        if (index !== currentSlide) {
                            e.target.style.background = '#fbcfe8';
                        }
                    }
                })
            )
        )
    );
};

// Ініціалізація після завантаження DOM
document.addEventListener('DOMContentLoaded', () => {
    const carouselRoot = document.getElementById('carousel-root');
    if (carouselRoot) {
        const root = ReactDOM.createRoot(carouselRoot);
        root.render(React.createElement(MonthlyScheduleCarousel));
    }
});