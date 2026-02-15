'use client';

const ASCII_LADY_JUSTICE = [
    '                               ___',
    '                            .-"   "-.',
    '                           /  .-. .- \\',
    '                          |  /   Y   |',
    '                          |  \\ . | . /            __|__',
    '                          |   "--^--"             \\ | /',
    '                          |    .---.                |',
    '                          |   /  _  \\            ___|___',
    '                      ____|  |  (_)  |          /   |   \\',
    '                   .-"    \\  \\  _  /          (    |    )',
    '                  /        "._" "-"_.           \\___|___/',
    '                 /   /\\         | |                 |',
    '                /   /  \\        | |                 |',
    '               /___/    \\_______| |_______          |',
    '                  /\\        /    |    \\             |',
    '                 /  \\______/     |     \\            |',
    '                /      /         |      \\           |',
    '               /______/          |       \\          |',
    '                  /\\             |        \\         |',
    '                 /  \\            |         \\        |',
    '                / /\\ \\           |          \\       |',
    '               /_/  \\_\\__________|___________\\      |',
    '                    /            |            \\     |',
    '                   /____________/ \\____________\\    |',
    '                        /                    \\      |',
    '                       /_________/  \\_________\\     |',
];

/**
 * Lady Justice hero art rendered as precomputed ASCII so it blends into the background.
 */
export default function LadyJustice({ className = '' }) {
    return (
        <figure className={`lady-ascii-wrap ${className}`.trim()}>
            <pre className="lady-ascii" role="img" aria-label="Lady Justice rendered in ASCII">
                {ASCII_LADY_JUSTICE.join('\n')}
            </pre>
        </figure>
    );
}
