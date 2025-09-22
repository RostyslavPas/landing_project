// PASUE Club Landing Page JavaScript
document.addEventListener('DOMContentLoaded', function() {

    // Navigation Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navbar = document.querySelector('.navbar');

    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navbar.classList.toggle('nav-active');
            navToggle.classList.toggle('active');
        });
    }

    // Smooth Scrolling for Search Boxes
    const searchBoxes = document.querySelectorAll('.search-box');
    searchBoxes.forEach(box => {
        const input = box.querySelector('input');
        if (input) {
            input.addEventListener('focus', function() {
                box.style.transform = 'translateY(-3px) scale(1.02)';
            });

            input.addEventListener('blur', function() {
                box.style.transform = 'translateY(0) scale(1)';
            });
        }
    });

    // Form Handling
    const ticketForm = document.querySelector('.ticket-form');
    const ticketPreview = document.querySelector('.ticket');

    if (ticketForm) {
        const nameInput = ticketForm.querySelector('#name');
        const phoneInput = ticketForm.querySelector('#phone');

        // Real-time ticket preview updates
        if (nameInput) {
            nameInput.addEventListener('input', function() {
                updateTicketPreview();
                addInputAnimation(this);
            });
        }

        if (phoneInput) {
            phoneInput.addEventListener('input', function() {
                updateTicketPreview();
                addInputAnimation(this);
            });
        }

        // Form submission
        ticketForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleFormSubmission();
        });
    }

    // Parallax Effect for Hero Elements
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.5;

        const heroElements = document.querySelectorAll('.rabbit-character, .chandelier');
        heroElements.forEach(element => {
            if (element) {
                element.style.transform = `translateY(${rate}px)`;
            }
        });

        // Header background opacity
        const header = document.querySelector('header');
        if (header) {
            const opacity = Math.min(scrolled / 100, 1);
            header.style.background = `rgba(254, 247, 240, ${0.95 + opacity * 0.05})`;
        }
    });

    // Intersection Observer for Animation
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe elements for animation
    const animateElements = document.querySelectorAll('.offer-item, .highlight-item, .guest-content, .ticket-form-container');
    animateElements.forEach(element => {
        observer.observe(element);
    });

    // Social Links Hover Effects
    const socialLinks = document.querySelectorAll('.social-links a');
    socialLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px) rotate(10deg)';
        });

        link.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) rotate(0deg)';
        });
    });

    // Dynamic Pricing Effect
    const priceDisplay = document.querySelector('.price-display');
    if (priceDisplay) {
        let priceAnimation;

        priceDisplay.addEventListener('mouseenter', function() {
            clearInterval(priceAnimation);
            let count = 0;
            const targetPrice = 1200;
            const increment = targetPrice / 30;

            priceAnimation = setInterval(() => {
                count += increment;
                if (count >= targetPrice) {
                    count = targetPrice;
                    clearInterval(priceAnimation);
                    this.innerHTML = `${Math.round(count)} грн ✨`;
                    setTimeout(() => {
                        this.innerHTML = `${targetPrice} грн`;
                    }, 1000);
                } else {
                    this.innerHTML = `${Math.round(count)} грн`;
                }
            }, 50);
        });
    }

    // Ticket Animation
    const ticket = document.querySelector('.ticket');
    if (ticket) {
        ticket.addEventListener('mouseenter', function() {
            this.style.transform = 'rotateY(10deg) translateY(-10px)';
            this.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.2)';
        });

        ticket.addEventListener('mouseleave', function() {
            this.style.transform = 'rotateY(0deg) translateY(0px)';
            this.style.boxShadow = '0 15px 40px rgba(0, 0, 0, 0.1)';
        });
    }

    // Special Guest Reveal Effect
    const guestImg = document.querySelector('.guest-images');
    if (guestImg) {
        guestImg.addEventListener('click', function() {
            this.style.filter = 'drop-shadow(0 20px 40px rgba(255, 107, 157, 0.5)) brightness(1.2)';
            setTimeout(() => {
                this.style.filter = 'drop-shadow(0 20px 40px rgba(0, 0, 0, 0.3))';
            }, 2000);
        });
    }

    // Loading Animation for Images
    const images = document.querySelectorAll('images');
    images.forEach(img => {
        img.addEventListener('load', function() {
            this.style.opacity = '0';
            this.style.transform = 'scale(1.1)';
            setTimeout(() => {
                this.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
                this.style.opacity = '1';
                this.style.transform = 'scale(1)';
            }, 100);
        });
    });

    // Functions
    function updateTicketPreview() {
        const name = document.querySelector('#name')?.value || 'Ваше ім\'я';
        const phone = document.querySelector('#phone')?.value || '';

        // Update ticket with user info (could be extended)
        const ticketBody = document.querySelector('.ticket-body');
        if (ticketBody && name !== 'Ваше ім\'я') {
            let nameElement = ticketBody.querySelector('.ticket-name');
            if (!nameElement) {
                nameElement = document.createElement('p');
                nameElement.classList.add('ticket-name');
                nameElement.style.fontWeight = '600';
                nameElement.style.color = '#ff6b9d';
                nameElement.style.marginTop = '10px';
                ticketBody.appendChild(nameElement);
            }
            nameElement.textContent = name;
        }
    }

    function addInputAnimation(input) {
        input.style.transform = 'scale(1.02)';
        setTimeout(() => {
            input.style.transform = 'scale(1)';
        }, 200);
    }

    function handleFormSubmission() {
        const submitBtn = document.querySelector('.submit-btn');
        const originalText = submitBtn.textContent;

        // Animate button
        submitBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        submitBtn.textContent = 'Обробляється...';
        submitBtn.disabled = true;

        // Simulate form processing
        setTimeout(() => {
            submitBtn.textContent = 'Успішно відправлено! ✅';

            // Add success animation to ticket
            const ticket = document.querySelector('.ticket');
            if (ticket) {
                ticket.style.transform = 'scale(1.05) rotateY(5deg)';
                ticket.style.boxShadow = '0 30px 60px rgba(40, 167, 69, 0.3)';
                ticket.style.border = '2px dashed #28a745';
            }

            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.style.background = 'linear-gradient(135deg, #ff6b9d 0%, #d63384 100%)';
                submitBtn.disabled = false;

                if (ticket) {
                    ticket.style.transform = 'scale(1) rotateY(0deg)';
                    ticket.style.boxShadow = '0 15px 40px rgba(0, 0, 0, 0.1)';
                    ticket.style.border = '2px dashed #ddd';
                }
            }, 3000);
        }, 2000);
    }

    // Easter Egg: Konami Code
    let konamiCode = [];
    const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA'];

    document.addEventListener('keydown', function(e) {
        konamiCode.push(e.code);
        if (konamiCode.length > konamiSequence.length) {
            konamiCode.shift();
        }

        if (konamiCode.join('') === konamiSequence.join('') && konamiCode.length === konamiSequence.length) {
            triggerEasterEgg();
        }
    });

    function triggerEasterEgg() {
        document.body.style.animation = 'rainbow 2s infinite';

        const style = document.createElement('style');
        style.textContent = `
            @keyframes rainbow {
                0% { filter: hue-rotate(0deg); }
                100% { filter: hue-rotate(360deg); }
            }
        `;
        document.head.appendChild(style);

        setTimeout(() => {
            document.body.style.animation = '';
            style.remove();
        }, 10000);

        // Show special message
        const message = document.createElement('div');
        message.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(45deg, #ff6b9d, #ffd700);
            color: white;
            padding: 20px 40px;
            border-radius: 20px;
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem;
            z-index: 10000;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        `;
        message.innerHTML = '🎉 Ви знайшли секретне повідомлення PASUE Club! 🎉';
        document.body.appendChild(message);

        setTimeout(() => {
            message.remove();
        }, 5000);
    }
});

// Add CSS animations
const styles = `
.animate-in {
    animation: slideInUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.nav-toggle.active span:nth-child(1) {
    transform: rotate(45deg) translate(5px, 5px);
}

.nav-toggle.active span:nth-child(2) {
    opacity: 0;
}

.nav-toggle.active span:nth-child(3) {
    transform: rotate(-45deg) translate(7px, -6px);
}

.search-box {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.form-group input {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.ticket {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.social-links a {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
`;

// Add styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);