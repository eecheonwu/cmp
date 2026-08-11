{
    "extends": [
        "@eslint/js/recommended",
        "plugin:react/recommended",
        "plugin:react-hooks/recommended",
        "plugin:@typescript-eslint/recommended"
    ],
        "parser": "@typescript-eslint/parser",
            "plugins": ["react", "@typescript-eslint"],
                "settings": {
        "react": {
            "version": "detect"
        }
    },
    "rules": {
        "react/react-in-jsx-scope": "off"
    }
}